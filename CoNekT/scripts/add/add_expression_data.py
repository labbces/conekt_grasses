#!/usr/bin/env python3

import getpass
import argparse
import json
import time

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select, insert

from crossref.restful import Works

from log_functions import *

# Create arguments
parser = argparse.ArgumentParser(description='Add expression data to the database')
parser.add_argument('--expression_matrix', type=str, metavar='matrix.txt',
                    dest='expression_file',
                    help='The expression_matrix.txt file from LSTrAP',
                    required=True)
parser.add_argument('--species_code', type=str, metavar='Svi',
                    dest='species_code',
                    help='The CoNekT Grasses species code',
                    required=True)
parser.add_argument('--sample_annotation', type=str, metavar='Sample Annotation File',
                    dest='sample_annotation',
                    help='Sample annotation file',
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



def add_literature(doi, engine):
    try:
        works = Works()
        literature_info = works.doi(doi)

        qtd_author = len(literature_info['author'])

        if 'family' in literature_info['author'][0]:
            author_names = literature_info['author'][0]['family']
        else:
            author_names = literature_info['author'][0]['name']

        title = literature_info['title']

        if 'published-print' in literature_info:
            public_year = literature_info['published-print']['date-parts'][0][0]
        elif 'published-online' in literature_info:
            public_year = literature_info['published-online']['date-parts'][0][0]
        else:
            public_year = literature_info['issued']['date-parts'][0][0]

        Session = sessionmaker(bind=engine)
        session = Session()

        # check if DOI already exists
        literature = session.query(LiteratureItem).filter(LiteratureItem.doi == doi).first()

        if not literature:
            new_literature = LiteratureItem(
                qtd_author=qtd_author,
                author_names=author_names,
                title=title,
                public_year=public_year,
                doi=doi
            )
            session.add(new_literature)
            session.commit()
            return new_literature
        else:
            return literature
    
    except Exception as e:
        print_log_error(logger, f'Error while inserting new literature: {e}')


def add_sample_po_association(sample_name, po_term, po_branch):
    """
    Create association between a sample and a Plant Ontology term.
    
    :param sample_name: sample identifier
    :param po_term: plant ontology term
    :param po_branch: branch type (e.g., po_anatomy, po_dev_stage)
    """

    try:
        # Step 1: Check if sample exists
        with engine.connect() as conn:
            stmt = select([Sample]).where(Sample.__table__.c.sample_name == sample_name)
            sample = conn.execute(stmt).first()

        if not sample:
            print_log_error(logger, f"Sample '{sample_name}' not found in database.")
            return

        # Step 2: Check if PO term exists
        with engine.connect() as conn:
            stmt = select([PlantOntology]).where(PlantOntology.__table__.c.po_term == po_term)
            po = conn.execute(stmt).first()

        if not po:
            print_log_error(logger, f"PO term '{po_term}' not found in database.")
            return

        # Step 3: Check if association already exists
        with engine.connect() as conn:
            stmt = select([SamplePOAssociation]).where(
                (SamplePOAssociation.__table__.c.sample_id == sample.id) &
                (SamplePOAssociation.__table__.c.po_id == po.id)
            )
            sample_po = conn.execute(stmt).first()

        if sample_po:
            logger.warning(f"⚠️ Association already exists: Sample='{sample.sample_name}' ↔ PO='{po.po_class}'")
            return

        # Step 4: Create association
        association = SamplePOAssociation(
            sample_id=sample.id,
            po_id=po.id,
            species_id=sample.species_id,
            po_branch=po_branch
        )

        session.add(association)
        session.commit()

    except Exception as e:
        session.rollback()
        print_log_error(logger, f"Error while creating PO association (Sample='{sample_name}', PO='{po_term}'): {e}")
    finally:
        session.close()


def add_sample_peco_association(sample_name, peco_term):
    """
    Create association between a sample and a Plant Experimental Conditions Ontology (PECO) term.
    
    :param sample_name: sample identifier
    :param peco_term: PECO ontology term
    """

    try:
        # Step 1: Get sample
        with engine.connect() as conn:
            stmt = select([Sample]).where(Sample.__table__.c.sample_name == sample_name)
            sample = conn.execute(stmt).first()

        if not sample:
            print_log_error(logger, f"Sample '{sample_name}' not found in database.")
            return

        # Step 2: Get PECO term
        with engine.connect() as conn:
            stmt = select([PlantExperimentalConditionsOntology]).where(
                PlantExperimentalConditionsOntology.__table__.c.peco_term == peco_term
            )
            peco = conn.execute(stmt).first()

        if not peco:
            print_log_error(logger, f"PECO term '{peco_term}' not found in database.")
            return

        # Step 3: Check if association exists
        with engine.connect() as conn:
            stmt = select([SamplePECOAssociation]).where(
                (SamplePECOAssociation.__table__.c.sample_id == sample.id) &
                (SamplePECOAssociation.__table__.c.peco_id == peco.id)
            )
            sample_peco = conn.execute(stmt).first()

        if sample_peco:
            logger.warning(f"⚠️ Association already exists: Sample='{sample.sample_name}' ↔ PECO='{peco.peco_class}'")
            return

        # Step 4: Create association
        association = SamplePECOAssociation(
            sample_id=sample.id,
            peco_id=peco.id,
            species_id=sample.species_id
        )

        session.add(association)
        session.commit()

    except Exception as e:
        session.rollback()
        print_log_error(logger, f"Error while creating PECO association (Sample='{sample_name}', PECO='{peco_term}'): {e}")
    finally:
        session.close()




from sqlalchemy import and_, insert

def add_sample_lit_association(sample_name, lit_doi, species_id, engine):
    """
    Create association between a sample and a Literature item (by DOI)
    compatible with automap_base and SQLAlchemy 1.3.3.
    """

    try:
        # Step 1: Get sample
        with engine.connect() as conn:
            sample = conn.execute(
                Sample.__table__.select().where(Sample.__table__.c.sample_name == sample_name)
            ).first()

        if not sample:
            print_log_error(logger, f"Sample '{sample_name}' not found in database while adding new literature association.")
            return

        # Step 2: Get or create Literature item
        with engine.connect() as conn:
            literature_item = conn.execute(
                LiteratureItem.__table__.select().where(LiteratureItem.__table__.c.doi == lit_doi)
            ).first()

        if not literature_item:
            logger.debug(f"Literature DOI '{lit_doi}' not found. Adding new entry...")
            literature_item = add_literature(lit_doi, engine)
            time.sleep(3)

        # Step 3: Check if association exists
        with engine.connect() as conn:
            sample_lit = conn.execute(
                SampleLitAssociation.__table__.select().where(
                    and_(
                        SampleLitAssociation.__table__.c.sample_id == sample.id,
                        SampleLitAssociation.__table__.c.literature_id == literature_item.id
                    )
                )
            ).first()

        if sample_lit:
            logger.warning(f"⚠️ Association already exists: Sample='{sample.sample_name}' ↔ DOI='{lit_doi}'")
            return

        # Step 4: Insert association using transaction
        with engine.begin() as conn:  # auto-commit/rollback
            conn.execute(
                insert(SampleLitAssociation.__table__).values(
                    sample_id=sample.id,
                    literature_id=literature_item.id,
                    species_id=species_id
                )
            )

    except Exception as e:
        print_log_error(logger, f"Error while creating Literature association (Sample='{sample_name}', DOI='{lit_doi}'): {e}")




def add_profile_from_lstrap(matrix_file, annotation_file, species_code, engine, order_color_file=None):
    """
    Function to convert an (normalized) expression matrix (lstrap output) into a profile

    :param matrix_file: path to the expression matrix
    :param annotation_file: path to the file assigning samples to conditions
    :param species_code: code of the species
    :param order_color_file: tab delimited file that contains the order and color of conditions
    """
    logger.info("______________________________________________________________________")
    logger.info(f"➡️  Adding expression profile for species '{species_code}'")

    # Step 1: Check if species exists
    try:
        logger.debug(f"Searching species '{species_code}' in database")
        with engine.connect() as conn:
            stmt = select([Species]).where(Species.__table__.c.code == species_code)
            species = conn.execute(stmt).first()

        if not species:
            print_log_error(logger, f"Species '{species_code}' not found in database.")
            exit(1)

        species_id = species.id
        logger.debug(f"✅ Species '{species_code}' found (ID: {species_id})")
    except Exception as e:
        print_log_error(logger, f"Database error while checking species '{species_code}': {e}")
        exit(1)

    # Step 2: Parse annotation file
    annotation = {}
    try:
        logger.debug(f"Reading annotation file: {annotation_file} and adding samples")
        with open(annotation_file, 'r') as fin:
            _ = fin.readline()  # skip header
            for line in fin:
                parts = line.split('\t')
                if len(parts) == 9:
                    run, literature_doi, description, replicate, strandness, layout, po_anatomy, po_dev_stage, peco = parts
                    peco = peco.rstrip()

                    session.add(Sample(
                        sample_name=run,
                        strandness=strandness,
                        layout=layout,
                        description=description,
                        replicate=replicate,
                        species_id=species_id
                    ))
                    session.commit()

                    annotation[run] = {
                        "description": description,
                        "replicate": replicate
                    }

                    # Mandatory po_anatomy
                    if po_anatomy:
                        annotation[run]["po_anatomy"] = po_anatomy
                        add_sample_po_association(run, po_anatomy, "po_anatomy")
                        with engine.connect() as conn:
                            stmt = select([PlantOntology]).where(PlantOntology.__table__.c.po_term == po_anatomy)
                            po = conn.execute(stmt).first()
                        annotation[run]["po_anatomy_class"] = po.po_class
                    else:
                        print_log_error(logger, f"Sample {run} missing mandatory 'po_anatomy'.")
                        exit(1)

                    # Optional po_dev_stage
                    if po_dev_stage:
                        annotation[run]["po_dev_stage"] = po_dev_stage
                        add_sample_po_association(run, po_dev_stage, "po_dev_stage")
                        with engine.connect() as conn:
                            stmt = select([PlantOntology]).where(PlantOntology.__table__.c.po_term == po_dev_stage)
                            po = conn.execute(stmt).first()
                        annotation[run]["po_dev_stage_class"] = po.po_class

                    # Optional peco
                    if peco:
                        annotation[run]["peco"] = peco
                        add_sample_peco_association(run, peco)
                        with engine.connect() as conn:
                            stmt = select([PlantExperimentalConditionsOntology]).where(
                                PlantExperimentalConditionsOntology.__table__.c.peco_term == peco
                            )
                            peco_details = conn.execute(stmt).first()
                        annotation[run]["peco_class"] = peco_details.peco_class

                else:
                    print_log_error(logger, f"Error parsing annotation line: {line}")
                    exit(1)

                # Add literature association
                add_sample_lit_association(run, literature_doi, species_id, engine)
                annotation[run]["lit_doi"] = literature_doi

        logger.debug(f"✅ Loaded {len(annotation)} samples from annotation file and added samples to database")
    except Exception as e:
        print_log_error(logger, f"Error parsing annotation file '{annotation_file}': {e}")
        exit(1)

    # Step 3: Order & Colors
    order, colors = [], []
    if order_color_file:
        logger.debug(f"Reading color file: {annotation_file}")
        try:
            with open(order_color_file, 'r') as fin:
                for line in fin:
                    try:
                        o, c = line.strip().split('\t')
                        order.append(o)
                        colors.append(c)
                    except Exception:
                        logger.warning(f"⚠️  Skipping invalid line in order/color file: {line.strip()}")
        except Exception as e:
            print_log_error(logger, f"Error reading order/color file '{order_color_file}': {e}")
            exit(1)

    # Step 4: Build sequence dictionary
    try:
        logger.debug(f"Building sequence dictionary")
        with engine.connect() as conn:
            stmt = select([Sequence]).where(
                (Sequence.__table__.c.species_id == species_id) &
                (Sequence.__table__.c.type == "protein_coding")
            )
            sequences = conn.execute(stmt).fetchall()

        sequence_dict = {s.name.upper(): s.id for s in sequences}
        logger.debug(f"Loaded {len(sequence_dict)} sequences for species '{species_code}'")
    except Exception as e:
        print_log_error(logger, f"Error loading sequences for species '{species_code}': {e}")
        exit(1)

    # Step 5: Parse expression matrix and insert profiles
    try:
        logger.debug(f"Parsing expression matrix and inserting profiles")
        added = 0
        with open(matrix_file) as fin:
            _, *colnames = fin.readline().rstrip().split()
            colnames = [c.replace('.htseq', '') for c in colnames]

            if not order:
                for c in colnames:
                    if c in annotation and annotation[c]['po_anatomy_class'] not in order:
                        order.append(annotation[c]['po_anatomy_class'])
                order.sort()

            new_probes = []
            for line in fin:
                transcript, *values = line.rstrip().split()
                profile = {
                    'tpm': {},
                    'annotation': {},
                    'replicate': {},
                    'po_anatomy': {},
                    'po_anatomy_class': {},
                    'po_dev_stage': {},
                    'po_dev_stage_class': {},
                    'peco': {},
                    'peco_class': {},
                    'lit_doi': {}
                }

                for c, v in zip(colnames, values):
                    if c in annotation:
                        profile['tpm'][c] = float(v)
                        profile['annotation'][c] = annotation[c]['description']
                        profile['replicate'][c] = annotation[c]['replicate']
                        profile['lit_doi'][c] = annotation[c]['lit_doi']
                        profile['po_anatomy'][c] = annotation[c]["po_anatomy"]
                        profile['po_anatomy_class'][c] = annotation[c]["po_anatomy_class"]

                        if 'po_dev_stage' in annotation[c]:
                            profile['po_dev_stage'][c] = annotation[c]["po_dev_stage"]
                            profile['po_dev_stage_class'][c] = annotation[c]["po_dev_stage_class"]
                        if 'peco' in annotation[c]:
                            profile['peco'][c] = annotation[c]["peco"]
                            profile['peco_class'][c] = annotation[c]["peco_class"]

                new_probe = {
                    "species_id": species_id,
                    "probe": transcript,
                    "sequence_id": sequence_dict.get(transcript.upper()),
                    "profile": json.dumps({
                        "order": order,
                        "colors": colors,
                        "data": profile
                    })
                }

                new_probes.append(new_probe)
                session.add(ExpressionProfile(**new_probe))
                added+=1

                if len(new_probes) > 400:
                    session.commit()
                    new_probes = []
                
                if added % 10000 == 0:
                    logger.debug(f"{added} expression profiles processed and committed...")

            session.commit()
            logger.info(f"✅ {added} expression profiles from '{matrix_file}' for {species_code} added successfully.")
    except Exception as e:
        session.rollback()
        print_log_error(logger, f"Error while processing matrix file '{matrix_file}': {e}")
        exit(1)
    finally:
        session.close()


try:

    thisFileName = os.path.basename(__file__)
    #log variables
    log_dir = args.log_dir  #log dir path
    log_file_name = "expression_data"   #log file names
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
    Sample = Base.classes.samples
    SampleLitAssociation = Base.classes.sample_literature
    PlantOntology = Base.classes.plant_ontology
    PlantExperimentalConditionsOntology = Base.classes.plant_experimental_conditions_ontology
    ExpressionProfile = Base.classes.expression_profiles
    SamplePOAssociation = Base.classes.sample_po
    SamplePECOAssociation = Base.classes.sample_peco
    LiteratureItem = Base.classes.literature

    # Create a Session
    Session = sessionmaker(bind=engine)
    session = Session()

    species_code = args.species_code
    matrix_file = args.expression_file
    annotation_file = args.sample_annotation

    # Adds expression profiles from LSTrAP
    add_profile_from_lstrap(matrix_file, annotation_file, species_code, engine)

    session.close()

except Exception as e:
    print_log_error(logger, e)
    logger.info(f" ---- ❌ An error occurred while executing {thisFileName}. Please fix the issue and rerun the script. ❌ ---- ")
    exit(1)


logger.info(f" ---- ✅ SUCCESS: All operations from {thisFileName} for '{species_code}' finished without errors! ✅ ---- ")