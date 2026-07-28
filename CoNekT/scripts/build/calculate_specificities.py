#!/usr/bin/env python3

import argparse
import json
from statistics import stdev
from math import sqrt, log2
from bisect import bisect

try:
    import numpy as np
    from scipy.stats import norm as _scipy_norm
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False


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

parser.add_argument('--z_val', type=float, metavar='Z value threshold',
                    dest='z_val',
                    help='Fallback Z-score multiplier for dist_ss when fuzzy z_val derivation '
                         'is disabled or scipy is unavailable (default: 1.0)',
                    required=False,
                    default=1.0)

parser.add_argument('--fuzzy_z_val', type=str, metavar='Use fuzzy z_val',
                    dest='fuzzy_z_val',
                    help='Derive z_val per DOI via Fuzzy c-means + inverse normal '
                         '(Lüleci & Yılmaz 2022). Falls back to --z_val if scipy is '
                         'unavailable or data is insufficient (true/false, default: true)',
                    required=False,
                    default="true")

parser.add_argument('--tau_threshold', type=float, metavar='Tau threshold',
                    dest='tau_threshold',
                    help='Min tau (on log2 means) to classify a gene as specifically expressed (default: 0.85)',
                    required=False,
                    default=0.85)

parser.add_argument('--min_expression', type=float, metavar='Minimum expression',
                    dest='min_expression',
                    help='Min raw mean TPM required in at least one condition (default: 10.0)',
                    required=False,
                    default=10.0)

parser.add_argument('--extended_tau_only', type=str, metavar='Extended Tau only',
                    dest='extended_tau_only',
                    help='Skip SPM calculation and run only Extended Tau (true/false, default: false)',
                    required=False,
                    default="false")

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
    if n < 2:
        return None

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


def _fuzzy_cmeans_1d(arr, m=2.0, max_iter=150, tol=1e-6):
    """
    1D Fuzzy c-means with c=2 clusters.
    Returns the membership weight of each element to the upper (higher centroid) cluster.
    Requires numpy.
    """
    arr = np.asarray(arr, dtype=float)
    if len(arr) < 2:
        return np.ones(len(arr), dtype=float)

    c_low = float(np.percentile(arr, 25))
    c_high = float(np.percentile(arr, 75))
    if c_low == c_high:
        c_low, c_high = float(np.min(arr)), float(np.max(arr))
    if c_low == c_high:
        return np.full(len(arr), 0.5)

    exp = 2.0 / (m - 1)
    for _ in range(max_iter):
        d_low  = np.maximum(np.abs(arr - c_low),  1e-10)
        d_high = np.maximum(np.abs(arr - c_high), 1e-10)
        u_high = 1.0 / (1.0 + (d_high / d_low) ** exp)
        u_low  = 1.0 - u_high

        new_c_high = float(np.sum((u_high ** m) * arr) / np.sum(u_high ** m))
        new_c_low  = float(np.sum((u_low  ** m) * arr) / np.sum(u_low  ** m))

        if abs(new_c_high - c_high) < tol and abs(new_c_low - c_low) < tol:
            break
        c_high, c_low = new_c_high, new_c_low

    return u_high


def _compute_doi_z_val(cond_value_lists, fallback_z_val=1.0, m=2.0):
    """
    Derives z_val for one DOI following Lüleci & Yılmaz (2022) Methods:
      1. For each condition: apply Fuzzy c-means (c=2) on non-zero mean-TPM values
         across all genes → ratio = n_up / n_total_nonzero
      2. Aggregate per-condition ratios → optimal_ratio (median across conditions)
      3. z_val = norm.ppf(optimal_ratio)

    Falls back to fallback_z_val when scipy is unavailable or data is insufficient.
    """
    if not _HAS_SCIPY:
        return fallback_z_val

    ratios = []
    for values in cond_value_lists.values():
        nonzero = np.array([v for v in values if v > 0], dtype=float)
        if len(nonzero) < 4:
            continue
        u_high = _fuzzy_cmeans_1d(nonzero, m=m)
        ratios.append(int(np.sum(u_high > 0.5)) / len(nonzero))

    if not ratios:
        return fallback_z_val

    optimal_ratio = float(np.clip(np.median(ratios), 1e-3, 1 - 1e-3))
    # Use (1 - ratio): small ratio (few genes in upper cluster) → high z_val (stringent threshold).
    # norm.ppf(ratio) would give negative z_val, pushing dist_ss above x_max (nothing qualifies).
    return float(_scipy_norm.ppf(1.0 - optimal_ratio))


def _get_or_create_method(engine, session, description, species_id, literature_id,
                          data_type, menu_order, conditions_json):
    """
    Idempotent method lookup/creation.

    If a method with the same description + species_id already exists, its existing
    expression_specificity rows are deleted (so pass 2 can re-insert cleanly) and its
    ID is returned. Otherwise a new ExpressionSpecificityMethod is created and its ID
    is returned. Returns None on error.
    """
    try:
        with engine.connect() as conn:
            existing = conn.execute(
                select([ExpressionSpecificityMethod.__table__.c.id])
                .where(ExpressionSpecificityMethod.__table__.c.description == description)
                .where(ExpressionSpecificityMethod.__table__.c.species_id == species_id)
            ).fetchone()
    except Exception as e:
        print_log_error(logger, f"Error looking up method '{description}': {e}")
        return None

    if existing:
        method_id = existing.id
        logger.info(f"Method already exists (ID {method_id}), clearing old specificities: {description}")
        try:
            session.execute(
                ExpressionSpecificity.__table__.delete()
                .where(ExpressionSpecificity.__table__.c.method_id == method_id)
            )
            session.commit()
        except Exception as e:
            session.rollback()
            print_log_error(logger, f"Failed to clear specificities for method {method_id}: {e}")
            return None
        return method_id

    new_method = ExpressionSpecificityMethod()
    new_method.species_id = species_id
    new_method.description = description
    new_method.literature_id = literature_id
    new_method.data_type = data_type
    new_method.menu_order = menu_order
    new_method.conditions = conditions_json

    try:
        session.add(new_method)
        session.commit()
        method_id = new_method.id
        session.expunge(new_method)
        logger.info(f"✅ Added new specificity method: {description}")
        return method_id
    except Exception as e:
        session.rollback()
        print_log_error(logger, f"Failed to add specificity method '{description}': {e}")
        return None


def extended_tau_conditions(means, z_val=1.0, tau_threshold=0.85, min_expression=10.0):
    """
    Returns the list of conditions qualifying as specifically expressed under Extended Tau
    (Lüleci & Yılmaz, 2022 - BioData Mining 15:31). Returns an empty list if the profile
    does not pass the specificity filters (i.e. the gene is not specifically expressed).

    :param means:           dict {condition: mean_tpm} — raw (non-log-transformed) values
    :param z_val:           Z-score multiplier for the statistical distance threshold
    :param tau_threshold:   minimum tau (computed on log2-transformed values) to proceed
    :param min_expression:  minimum raw mean TPM required in at least one condition
    :return: list of qualifying condition names (may be empty)
    """
    if not means or len(means) < 2:
        return []

    raw_values = list(means.values())

    if max(raw_values) < min_expression:
        return []

    log2_values = [log2(v + 1) for v in raw_values]
    profile_tau = tau(log2_values)

    if profile_tau is None or profile_tau < tau_threshold:
        return []

    x_max = max(raw_values)
    non_zero_vals = [v for v in raw_values if v > 0]
    # stdev requires >= 2 points; with only 1 non-zero value sigma=0 → only the maximum qualifies
    sigma = stdev(non_zero_vals) if len(non_zero_vals) >= 2 else 0.0

    dist_ss = x_max - sigma * z_val

    return [cond for cond, v in means.items() if v >= dist_ss]


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

    CATEGORIES = ['annotation', 'po_anatomy_class', 'po_dev_stage_class', 'peco_class']

    stmt = select([
        ExpressionProfile.__table__.c.id,
        ExpressionProfile.__table__.c.profile
    ]).where(ExpressionProfile.__table__.c.species_id == species_id)

    # Two-pass approach per category — O(1) peak RAM per profile:
    #   Pass 1 (lightweight): collect unique condition strings per DOI to build methods.
    #   Pass 2: stream profiles one at a time, compute specificity, write and discard immediately.
    # stream_results=True prevents PyMySQL from buffering all rows client-side before iteration.
    for sample_category in CATEGORIES:

        logger.info(f"Processing category '{sample_category}'")

        # --- Pass 1: collect conditions per DOI ---
        doi_conditions = {}  # {doi: set of condition strings}

        try:
            with engine.connect().execution_options(stream_results=True) as conn:
                for _, profile_json in conn.execute(stmt):
                    try:
                        data = json.loads(profile_json)['data']
                        cat_map = data.get(sample_category, {})
                        for sample, doi in data.get('lit_doi', {}).items():
                            cond = cat_map.get(sample)
                            if cond:
                                doi_conditions.setdefault(doi, set()).add(cond)
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to parse profile in pass 1: {e}")
        except Exception as e:
            print_log_error(logger, f"Error in pass 1 for category '{sample_category}': {e}")
            exit(1)

        logger.debug(f"Pass 1 complete: {len(doi_conditions)} DOI(s) found for '{sample_category}'")

        # Create ExpressionSpecificityMethod for each DOI with >= 2 conditions
        doi_methods = {}  # {doi: method_id}

        for doi, conditions in doi_conditions.items():
            if len(conditions) < 2:
                logger.debug(f"Skipping DOI '{doi}' — fewer than 2 conditions in '{sample_category}'.")
                continue

            try:
                with engine.connect() as conn:
                    literature = conn.execute(
                        select([LiteratureItem.__table__.c.id,
                                LiteratureItem.__table__.c.author_names,
                                LiteratureItem.__table__.c.public_year,
                                LiteratureItem.__table__.c.doi])
                        .where(LiteratureItem.__table__.c.doi == doi)
                    ).fetchone()

                if not literature:
                    logger.warning(f"⚠️ Literature '{doi}' not found in database. Skipping.")
                    continue
            except Exception as e:
                print_log_error(logger, f"Error retrieving literature '{doi}': {e}")
                continue

            sample_category_method = sample_category.replace('_class', '')
            method_description = f"{sample_category_method} ({literature.author_names}, {literature.public_year} - {literature.doi})"

            method_id = _get_or_create_method(
                engine, session,
                description=method_description,
                species_id=species_id,
                literature_id=literature.id,
                data_type="condition",
                menu_order=0,
                conditions_json=json.dumps(sorted(list(conditions))),
            )
            if method_id is not None:
                doi_methods[doi] = method_id

        if not doi_methods:
            logger.info(f"No methods for category '{sample_category}'. Skipping pass 2.")
            continue

        # --- Pass 2: stream profiles and write specificities one by one ---
        specificities_buffer = []

        try:
            with engine.connect().execution_options(stream_results=True) as conn:
                row_count = 0
                for profile_id, profile_json in conn.execute(stmt):
                    try:
                        data = json.loads(profile_json)['data']
                        cat_map = data.get(sample_category, {})
                        tpm_map = data.get('tpm', {})

                        # Aggregate TPM per (doi, condition) for this single profile only
                        doi_cond_tpms = {}  # {doi: {condition: [sum, count]}}
                        for sample, doi in data.get('lit_doi', {}).items():
                            if doi not in doi_methods:
                                continue
                            cond = cat_map.get(sample)
                            if not cond:
                                continue
                            tpm_val = float(tpm_map.get(sample, 0))
                            entry = doi_cond_tpms.setdefault(doi, {})
                            if cond in entry:
                                entry[cond][0] += tpm_val
                                entry[cond][1] += 1
                            else:
                                entry[cond] = [tpm_val, 1]

                        for doi, cond_entries in doi_cond_tpms.items():
                            means = {cond: s / c for cond, (s, c) in cond_entries.items()}
                            if len(means) < 2:
                                continue
                            profile_tau = tau(means.values())
                            profile_extended_tau = tau([log2(v + 1) for v in means.values()])
                            profile_entropy = entropy_from_values(means.values())

                            profile_specificities = [
                                {
                                    "profile_id": profile_id,
                                    "condition": cond,
                                    "score": expression_specificity(cond, means),
                                    "entropy": profile_entropy,
                                    "tau": profile_tau,
                                    "extended_tau": profile_extended_tau,
                                    "method_id": doi_methods[doi],
                                }
                                for cond in means
                            ]
                            profile_specificities.sort(key=lambda x: x["score"], reverse=True)
                            if profile_specificities:
                                top = profile_specificities[0]
                                specificities_buffer.append(top)
                                session.add(ExpressionSpecificity(**top))

                        row_count += 1
                        if len(specificities_buffer) >= 400:
                            session.commit()
                            session.expunge_all()
                            specificities_buffer.clear()

                        if row_count % 10000 == 0:
                            logger.debug(f"{row_count} profiles processed for '{sample_category}'...")

                    except Exception as e:
                        print_log_error(logger, f"Failed to calculate specificities for profile {profile_id}: {e}")

            session.commit()
            session.expunge_all()
            logger.info(f"✅ Pass 2 complete for category '{sample_category}': {row_count} profiles processed.")
        except Exception as e:
            session.rollback()
            print_log_error(logger, f"Error in pass 2 for category '{sample_category}': {e}")


def calculate_extended_tau_specificities(species_code, engine,
                                          z_val=1.0, tau_threshold=0.85, min_expression=10.0,
                                          use_fuzzy_z_val=True):
    """
    Calculates Extended Tau expression specificities (Lüleci & Yılmaz, 2022 - BioData Mining 15:31)
    and stores them in the database. Unlike calculate_specificities(), which stores only the single
    top-scoring condition per (profile, method), this function stores one ExpressionSpecificity
    record per qualifying condition, enabling one-to-many gene→condition assignments.

    Three streaming passes per category:
      Pass 1     : collect unique condition strings per DOI (build methods).
      Pass 1.5   : collect mean-TPM distributions per (DOI, condition) → derive z_val per DOI
                   via Fuzzy c-means + inverse normal (skipped when use_fuzzy_z_val=False).
      Pass 2     : compute extended tau per profile, write all qualifying records immediately.

    :param species_code:     Species code string
    :param engine:           SQLAlchemy engine (automap-reflected)
    :param z_val:            Fallback Z-score multiplier (used when fuzzy derivation is off or fails)
    :param tau_threshold:    Minimum tau (on log2 values) for a gene to be considered specific
    :param min_expression:   Minimum raw mean TPM required in at least one condition
    :param use_fuzzy_z_val:  If True, derive z_val per DOI from data (Fuzzy c-means + norm.ppf)
    """

    logger.info("______________________________________________________________________")
    logger.info(f"➡️  Calculating Extended Tau specificities for species '{species_code}'")
    z_val_mode = "fuzzy (Fuzzy c-means + norm.ppf per DOI)" if (use_fuzzy_z_val and _HAS_SCIPY) else \
                 f"fixed = {z_val}" + (" [fuzzy requested but scipy unavailable]" if use_fuzzy_z_val else "")
    logger.info(f"   z_val mode    : {z_val_mode}")
    logger.info(f"   tau_threshold : {tau_threshold}")
    logger.info(f"   min_expression: {min_expression}")

    try:
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

    CATEGORIES = ['annotation', 'po_anatomy_class', 'po_dev_stage_class', 'peco_class']

    stmt = select([
        ExpressionProfile.__table__.c.id,
        ExpressionProfile.__table__.c.profile
    ]).where(ExpressionProfile.__table__.c.species_id == species_id)

    for sample_category in CATEGORIES:

        logger.info(f"[Extended Tau] Processing category '{sample_category}'")

        # --- Pass 1: collect conditions per DOI (identical to SPM pass 1) ---
        doi_conditions = {}  # {doi: set of condition strings}

        try:
            with engine.connect().execution_options(stream_results=True) as conn:
                for _, profile_json in conn.execute(stmt):
                    try:
                        data = json.loads(profile_json)['data']
                        cat_map = data.get(sample_category, {})
                        for sample, doi in data.get('lit_doi', {}).items():
                            cond = cat_map.get(sample)
                            if cond:
                                doi_conditions.setdefault(doi, set()).add(cond)
                    except Exception as e:
                        logger.warning(f"⚠️ [Extended Tau] Failed to parse profile in pass 1: {e}")
        except Exception as e:
            print_log_error(logger, f"[Extended Tau] Error in pass 1 for category '{sample_category}': {e}")
            exit(1)

        logger.debug(f"[Extended Tau] Pass 1 complete: {len(doi_conditions)} DOI(s) found for '{sample_category}'")

        # Create ExpressionSpecificityMethod for each DOI with >= 2 conditions
        doi_methods = {}  # {doi: method_id}

        for doi, conditions in doi_conditions.items():
            if len(conditions) < 2:
                logger.debug(f"[Extended Tau] Skipping DOI '{doi}' — fewer than 2 conditions in '{sample_category}'.")
                continue

            try:
                with engine.connect() as conn:
                    literature = conn.execute(
                        select([LiteratureItem.__table__.c.id,
                                LiteratureItem.__table__.c.author_names,
                                LiteratureItem.__table__.c.public_year,
                                LiteratureItem.__table__.c.doi])
                        .where(LiteratureItem.__table__.c.doi == doi)
                    ).fetchone()

                if not literature:
                    logger.warning(f"⚠️ [Extended Tau] Literature '{doi}' not found in database. Skipping.")
                    continue
            except Exception as e:
                print_log_error(logger, f"[Extended Tau] Error retrieving literature '{doi}': {e}")
                continue

            sample_category_method = sample_category.replace('_class', '')
            method_description = (
                f"extended_tau_{sample_category_method} "
                f"({literature.author_names}, {literature.public_year} - {literature.doi})"
            )

            method_id = _get_or_create_method(
                engine, session,
                description=method_description,
                species_id=species_id,
                literature_id=literature.id,
                data_type="condition",
                menu_order=0,
                conditions_json=json.dumps(sorted(list(conditions))),
            )
            if method_id is not None:
                doi_methods[doi] = method_id

        if not doi_methods:
            logger.info(f"[Extended Tau] No methods for category '{sample_category}'. Skipping pass 2.")
            continue

        # --- Pass 1.5: compute data-driven z_val per DOI (Lüleci & Yılmaz 2022) ---
        if use_fuzzy_z_val and _HAS_SCIPY:
            doi_cond_values = {doi: {} for doi in doi_methods}

            try:
                with engine.connect().execution_options(stream_results=True) as conn:
                    for _, profile_json in conn.execute(stmt):
                        try:
                            data    = json.loads(profile_json)['data']
                            cat_map = data.get(sample_category, {})
                            tpm_map = data.get('tpm', {})

                            doi_cond_sums = {}
                            for sample, doi in data.get('lit_doi', {}).items():
                                if doi not in doi_methods:
                                    continue
                                cond = cat_map.get(sample)
                                if not cond:
                                    continue
                                tpm_val = float(tpm_map.get(sample, 0))
                                entry = doi_cond_sums.setdefault(doi, {})
                                if cond in entry:
                                    entry[cond][0] += tpm_val
                                    entry[cond][1] += 1
                                else:
                                    entry[cond] = [tpm_val, 1]

                            for doi, cond_entries in doi_cond_sums.items():
                                doi_bucket = doi_cond_values[doi]
                                for cond, (s, c) in cond_entries.items():
                                    doi_bucket.setdefault(cond, []).append(s / c)
                        except Exception:
                            pass
            except Exception as e:
                print_log_error(logger, f"[Extended Tau] Error in pass 1.5 for '{sample_category}': {e}")

            doi_z_vals = {}
            for doi, cond_value_lists in doi_cond_values.items():
                doi_z_vals[doi] = _compute_doi_z_val(cond_value_lists, fallback_z_val=z_val)
                logger.info(f"  [Extended Tau] '{doi[:50]}': z_val = {doi_z_vals[doi]:.4f}")
            del doi_cond_values
        else:
            doi_z_vals = {doi: z_val for doi in doi_methods}
            logger.info(f"  [Extended Tau] Using fixed z_val = {z_val} for all DOIs.")

        # --- Pass 2: stream profiles, apply extended tau, store all qualifying conditions ---
        specificities_buffer = []

        try:
            with engine.connect().execution_options(stream_results=True) as conn:
                row_count = 0
                for profile_id, profile_json in conn.execute(stmt):
                    try:
                        data = json.loads(profile_json)['data']
                        cat_map = data.get(sample_category, {})
                        tpm_map = data.get('tpm', {})

                        # Aggregate TPM per (doi, condition) — identical to SPM pass 2
                        doi_cond_tpms = {}  # {doi: {condition: [sum, count]}}
                        for sample, doi in data.get('lit_doi', {}).items():
                            if doi not in doi_methods:
                                continue
                            cond = cat_map.get(sample)
                            if not cond:
                                continue
                            tpm_val = float(tpm_map.get(sample, 0))
                            entry = doi_cond_tpms.setdefault(doi, {})
                            if cond in entry:
                                entry[cond][0] += tpm_val
                                entry[cond][1] += 1
                            else:
                                entry[cond] = [tpm_val, 1]

                        for doi, cond_entries in doi_cond_tpms.items():
                            means = {cond: s / c for cond, (s, c) in cond_entries.items()}

                            qualifying_conds = extended_tau_conditions(
                                means, z_val=doi_z_vals.get(doi, z_val),
                                tau_threshold=tau_threshold,
                                min_expression=min_expression,
                            )

                            if not qualifying_conds:
                                continue

                            log2_values = [log2(v + 1) for v in means.values()]
                            profile_tau = tau(log2_values)
                            profile_entropy = entropy_from_values(means.values())

                            for cond in qualifying_conds:
                                record = {
                                    "profile_id": profile_id,
                                    "condition": cond,
                                    "score": expression_specificity(cond, means),
                                    "entropy": profile_entropy,
                                    "tau": profile_tau,
                                    "method_id": doi_methods[doi],
                                }
                                specificities_buffer.append(record)
                                session.add(ExpressionSpecificity(**record))

                        row_count += 1
                        if len(specificities_buffer) >= 400:
                            session.commit()
                            session.expunge_all()
                            specificities_buffer.clear()

                        if row_count % 10000 == 0:
                            logger.debug(f"[Extended Tau] {row_count} profiles processed for '{sample_category}'...")

                    except Exception as e:
                        print_log_error(logger, f"[Extended Tau] Failed for profile {profile_id}: {e}")

            session.commit()
            session.expunge_all()
            logger.info(f"✅ [Extended Tau] Pass 2 complete for category '{sample_category}': {row_count} profiles processed.")
        except Exception as e:
            session.rollback()
            print_log_error(logger, f"[Extended Tau] Error in pass 2 for category '{sample_category}': {e}")


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

    # Extend MySQL session timeouts to survive multi-hour streaming queries.
    # Without this, the server drops the TCP connection mid-stream (errno 104 / error 2013).
    engine = create_engine(
        create_engine_string,
        echo=db_verbose,
        connect_args={
            "init_command": (
                "SET SESSION wait_timeout=86400, "
                "SESSION interactive_timeout=86400, "
                "SESSION net_read_timeout=86400, "
                "SESSION net_write_timeout=86400"
            )
        }
    )

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
    extended_tau_only = str2bool(args.extended_tau_only)
    use_fuzzy_z_val   = str2bool(args.fuzzy_z_val)

    if not extended_tau_only:
        calculate_specificities(species_code, engine)

    calculate_extended_tau_specificities(
        species_code, engine,
        z_val=args.z_val,
        tau_threshold=args.tau_threshold,
        min_expression=args.min_expression,
        use_fuzzy_z_val=use_fuzzy_z_val,
    )

    session.close()

except Exception as e:
    print_log_error(logger, e)
    logger.info(f" ---- ❌ An error occurred while executing {thisFileName}. Please fix the issue and rerun the script. ❌ ---- ")
    exit(1)

logger.info(f" ---- ✅ SUCCESS: All operations from {thisFileName} for '{species_code}' finished without errors! ✅ ---- ")