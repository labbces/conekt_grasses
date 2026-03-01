#!/usr/bin/env python3

import argparse
import json
from statistics import mean
from math import sqrt, log2
from bisect import bisect
from collections import defaultdict


from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select

import sys, os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from add.log_functions import *

# Create arguments
parser = argparse.ArgumentParser(description='Calculate specificity for a species')
parser.add_argument('--species_code', type=str, metavar='Svi',
                    dest='species_code',
                    help='The species code as used in CoNekT Grasses',
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

parser.add_argument('--first_run', type=str, metavar='Flag indicating first execution of the file',
                    dest='first_run',
                    help='Controls log file opening type',
                    required=False,
                    default="true")

args = parser.parse_args()

if args.db_password:
    db_password = args.db_password
else:
    db_password = input("Enter the database password: ")


def tau(values):
    """
    Calculates the Tau value for a list of expression values

    :param dist: list of values
    :return: tau value
    """
    n = len(values)                   # number of values
    mxi = max(values)                 # max value

    if mxi > 0:
        t = sum([1 - (x/mxi) for x in values])/(n - 1)

        return t
    else:
        return None


def dot_prod(a, b):
    """
    Calculates the dot product of two lists with values

    :param a: first list
    :param b: second list
    :return: dot product (a . b)
    """
    return sum([i*j for (i, j) in zip(a, b)])


def norm(a):
    """
    Calculates the Frobenius norm for a list of values

    :param a: list of values
    :return: the Frobenius norm
    """
    return sqrt(sum([i**2 for i in a]))


def expression_specificity(condition, profile):

    values = [v for k, v in profile.items()]
    vector = [v if k == condition else 0 for k, v in profile.items()]

    dot_product = dot_prod(values, vector)

    mul_len = norm(values) * norm(vector)

    return dot_product/mul_len if mul_len != 0 else 0


def entropy(dist):
    """
    Calculates the entropy for a given distribution (!)

    :param dist: list with the counts for each bin
    :return: entropy
    """
    e = 0
    l = sum(dist)

    for d in dist:
        d_x = d/l
        if d_x > 0:
            e += - d_x*log2(d_x)

    return e


def entropy_from_values(values, num_bins=20):
    """
    builds the distribution and calculates the entropy for a list of values


    :param values: list of values
    :param num_bins: number of bins to generate for the distribution, default 20
    :return: entropy
    """

    hist = []

    bins = [b/num_bins for b in range(0, num_bins)]

    v_max = max(values)

    if v_max > 0:
        n_values = [v/v_max for v in values]
        hist = [0] * num_bins

        for v in n_values:
            b = bisect(bins, v)
            hist[b-1] += 1

    return entropy(hist)


def calculate_specificities(species_code, engine):
    """
    Calculates expression specificities for a given species and stores them in the database.

    :param species_code: Species code to identify the species in the database
    :param engine: SQLAlchemy engine
    """

    logger.info("______________________________________________________________________")
    logger.info(f"➡️  Calculating expression specificities for species '{species_code}'")

    try:
        logger.debug(f"Searching species '{species_code}' in database")
        species = session.query(Species).filter(Species.code == species_code).first()
        if species:
            species_id = species.id
            logger.debug(f"✅ Species '{species_code}' found (ID: {species_id})")
        else:
            logger.error(f"❌ Species '{species_code}' not found in database.")
            exit(1)
    except Exception as e:
        print_log_error(logger, f"Error while querying species '{species_code}': {e}")
        exit(1)

    if not species_id:
        print_log_error(logger, f"Species '{species_code}' not found in database.")
        exit(1)

    try:
        # Retrieve expression profiles (ORM free for performance)
        logger.debug(f"Retrieving expression profiles for '{species_code}'")
        with engine.connect() as conn:
            stmt = select([
                ExpressionProfile.__table__.c.id,
                ExpressionProfile.__table__.c.profile
            ]).where(ExpressionProfile.__table__.c.species_id == species_id)
            profiles = conn.execute(stmt).fetchall()   # ✅ fetchall em vez de all()

        logger.debug(f"Retrieved {len(profiles)} expression profiles for species '{species_code}'")
    except Exception as e:
        print_log_error(logger, f"Error while retrieving expression profiles: {e}")
        exit(1)


    # Collect all literature items (DOIs) from profiles
    sample_literature_items = set()
    for profile_id, profile in profiles:
        try:
            profile_data = json.loads(profile)
            sample_literature_items |= set(profile_data['data']['lit_doi'].values())
        except Exception as e:
            logger.warning(f"⚠️  Failed to parse profile {profile_id}: {e}")

    logger.debug(f"Found {len(sample_literature_items)} unique literature items.")

    # Iterate through categories of conditions
    for sample_category in ['annotation', 'po_anatomy_class', 'po_dev_stage_class', 'peco_class']:

        logger.info(f"Processing category '{sample_category}'")

        for lit_doi in sample_literature_items:
            try:
                # Retrieve literature record
                with engine.connect() as conn:
                    stmt = select([LiteratureItem.__table__.c.id,
                                LiteratureItem.__table__.c.author_names,
                                LiteratureItem.__table__.c.public_year,
                                LiteratureItem.__table__.c.doi])\
                        .where(LiteratureItem.__table__.c.doi == lit_doi)
                    literature = conn.execute(stmt).fetchone()

                if not literature:
                    logger.warning(f"⚠️ Literature '{lit_doi}' not found in database. Skipping.")
                    continue

            except Exception as e:
                print_log_error(logger, f"Error while retrieving literature '{lit_doi}': {e}")
                continue

            # Create new specificity method
            sample_category_method = sample_category.replace('_class', '')
            new_method = ExpressionSpecificityMethod()
            new_method.species_id = species_id
            new_method.description = f"{sample_category_method} ({literature.author_names}, {literature.public_year} - {literature.doi})"
            new_method.literature_id = literature.id
            new_method.data_type = "condition"
            new_method.menu_order = 0

            # Collect annotations for this category and literature
            sample_annotations = set()
            for profile_id, profile in profiles:
                profile_data = json.loads(profile)
                for k, v in profile_data['data'][sample_category].items():
                    if profile_data['data']['lit_doi'][k] == lit_doi:
                        sample_annotations.add(v)

            if len(sample_annotations) < 2:
                logger.debug(f"Skipping {sample_category} - not enough annotations for lit_doi {lit_doi}.")
                continue

            new_method.conditions = json.dumps(list(sample_annotations))

            try:
                session.add(new_method)
                session.commit()
                logger.info(f"✅ Added new specificity method: {new_method.description}")
            except Exception as e:
                session.rollback()
                print_log_error(logger, f"Failed to add specificity method '{new_method.description}': {e}")
                continue

            # Now calculate specificities for each profile
            specificities = []
            for profile_id, profile in profiles:
                try:
                    profile_data = json.loads(profile)

                    # Collect expression values grouped by condition
                    profile_annotation_values = defaultdict(list)
                    for k, v in profile_data['data']['tpm'].items():
                        if profile_data['data']['lit_doi'][k] == lit_doi:
                            if k in profile_data['data'][sample_category]:
                                condition = profile_data['data'][sample_category][k]
                                profile_annotation_values[condition].append(v)

                    # Calculate mean TPM per condition
                    profile_annotation_means = {k: mean(v) for k, v in profile_annotation_values.items()}

                    # Calculate SPM-related metrics
                    profile_tau = tau(profile_annotation_means.values())
                    profile_entropy = entropy_from_values(profile_annotation_means.values())

                    # Calculate specificity scores
                    profile_specificities = []
                    for condition in profile_annotation_values.keys():
                        score = expression_specificity(condition, profile_annotation_means)
                        new_specificity = {
                            "profile_id": profile_id,
                            "condition": condition,
                            "score": score,
                            "entropy": profile_entropy,
                            "tau": profile_tau,
                            "method_id": new_method.id,
                        }
                        profile_specificities.append(new_specificity)

                    # Sort and keep only the top condition
                    profile_specificities.sort(key=lambda x: x["score"], reverse=True)
                    if profile_specificities:
                        top_specificity = profile_specificities[0]
                        specificities.append(top_specificity)
                        session.add(ExpressionSpecificity(**top_specificity))

                    # Commit in batches for performance
                    if len(specificities) > 400:
                        session.commit()
                        specificities.clear()

                except Exception as e:
                    print_log_error(logger, f"Failed to calculate specificities for profile {profile_id}: {e}")

            # Commit remaining specificities
            try:
                session.commit()
                logger.info(f"✅ Specificities committed for category '{sample_category}' and literature '{lit_doi}'")
            except Exception as e:
                session.rollback()
                print_log_error(logger, f"Failed to commit specificities for '{lit_doi}': {e}")


try:
    thisFileName = os.path.basename(__file__)

    # Log variables
    log_dir = args.log_dir
    log_file_name = "calculate_specificities"  # e.g. "gene_ontologies"
    db_verbose = str2bool(args.db_verbose)
    py_verbose = str2bool(args.py_verbose)
    first_run = str2bool(args.first_run)

    logger = setup_logger(log_dir=log_dir,
                          base_filename=log_file_name,
                          DBverbose=db_verbose,
                          PYverbose=py_verbose,
                          overwrite_logs=first_run)
        
    db_admin = args.db_admin
    db_name = args.db_name

    create_engine_string = "mysql+pymysql://"+db_admin+":"+db_password+"@localhost/"+db_name

    engine = create_engine(create_engine_string, echo=db_verbose)

    # Reflect an existing database into a new model
    Base = automap_base()

    # Use the engine to reflect the database
    Base.prepare(engine, reflect=True)

    Species = Base.classes.species
    ExpressionSpecificityMethod = Base.classes.expression_specificity_method
    ExpressionSpecificity = Base.classes.expression_specificity
    ExpressionProfile = Base.classes.expression_profiles
    LiteratureItem = Base.classes.literature

    # Create a Session
    Session = sessionmaker(bind=engine)
    session = Session()

    species_code = args.species_code

    # Run function(s) to calculate expression specificity
    calculate_specificities(species_code, engine)

    session.close()

except Exception as e:
    print_log_error(logger, e)
    logger.info(f" ---- ❌ An error occurred while executing {thisFileName}. Please fix the issue and rerun the script. ❌ ---- ")
    exit(1)

logger.info(f" ---- ✅ SUCCESS: All operations from {thisFileName} for '{species_code}' finished without errors! ✅ ---- ")