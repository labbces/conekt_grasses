#!/usr/bin/env python3

import argparse
import json
from statistics import mean
from math import sqrt, log2
from bisect import bisect

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select

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
    Function calculates specific genes based on the expression.

    :param species_id: internal species ID
    :param description: description for the method to determine the specificity
    :return id of the new method
    """

    with engine.connect() as conn:
        stmt = select(Species).where(Species.__table__.c.code == species_code)
        species_id = conn.execute(stmt).first().id

    if not species_id:
        print(f'Species not found in database: {species_code}')
        exit(1)
    
    # get profile from the database (ORM free for speed)
    with engine.connect() as conn:
        stmt = select(ExpressionProfile.__table__.c.id,
                        ExpressionProfile.__table__.c.profile)\
                        .where(ExpressionProfile.__table__.c.species_id == species_id)
        profiles = conn.execute(stmt).all()

    sample_literature_items = {}

    for profile_id, profile in profiles:
        profile_data = json.loads(profile)
        sample_literature_items = set(sample_literature_items).union(set(profile_data['data']['lit_doi'].values()))

    for sample_category in ['annotation', 'po_anatomy_class', 'po_dev_stage_class', 'peco_class']:

        for lit_doi in sample_literature_items:

            # detect all sample annotations
            sample_annotations = {}

            with engine.connect() as conn:
                stmt = select(LiteratureItem).where(LiteratureItem.__table__.c.doi == lit_doi)
                literature = conn.execute(stmt).first()

            if not literature:
                print(f'Literature not found in database: {lit_doi}')
                exit(1)

            sample_category_method = sample_category.replace('_class', '')

            new_method = ExpressionSpecificityMethod()
            new_method.species_id = species_id
            new_method.description = f'{sample_category_method} ({literature.author_names}, {literature.public_year} - {literature.doi})'
            new_method.literature_id = literature.id
            new_method.data_type = 'condition'
            new_method.menu_order = 0

            for profile_id, profile in profiles:
                profile_data = json.loads(profile)
                for k, v in profile_data['data'][sample_category].items():
                    if profile_data['data']['lit_doi'][k] == lit_doi:
                        sample_annotations = set(sample_annotations).union(set([profile_data['data'][sample_category][k]]))

            if len(sample_annotations) < 2:
                continue

            new_method.conditions = json.dumps(list(sample_annotations))

            session.add(new_method)
            session.commit()

            # detect specifities and add to the database
            specificities = []

            for profile_id, profile in profiles:

                # prepare profile data for calculation
                profile_data = json.loads(profile)

                profile_annotation_values = {}
                profile_annotation_means = {}

                for k, v in profile_data['data']['tpm'].items():
                    if profile_data['data']['lit_doi'][k] == lit_doi:
                        if k in profile_data['data'][sample_category].keys():
                            if profile_data['data'][sample_category][k] in profile_annotation_values.keys():
                                profile_annotation_values[profile_data['data'][sample_category][k]].append(v)
                            else:
                                profile_annotation_values[profile_data['data'][sample_category][k]] = [v]
                
                for k, v in profile_annotation_values.items():
                    profile_annotation_means[k] = mean(v)
            
                # determine spm score for each condition
                profile_specificities = []
                profile_tau = tau(profile_annotation_means.values())
                profile_entropy = entropy_from_values(profile_annotation_means.values())

                for sample_annotation in profile_annotation_values.keys():
                    score = expression_specificity(sample_annotation, profile_annotation_means)
                    new_specificity = {
                        'profile_id': profile_id,
                        'condition': sample_annotation,
                        'score': score,
                        'entropy': profile_entropy,
                        'tau': profile_tau,
                        'method_id': new_method.id,
                    }

                    profile_specificities.append(new_specificity)

                # sort conditions and add top one
                profile_specificities = sorted(profile_specificities, key=lambda x: x['score'], reverse=True)

                specificities.append(profile_specificities[0])
                session.add(ExpressionSpecificity(**profile_specificities[0]))

                # write specificities to db if there are more than 400 (ORM free for speed)
                if len(specificities) > 400:
                    session.commit()
                    specificities = []

            # write remaining specificities to the db
            session.commit()

        
db_admin = args.db_admin
db_name = args.db_name

create_engine_string = "mysql+pymysql://"+db_admin+":"+db_password+"@localhost/"+db_name

engine = create_engine(create_engine_string, echo=True)

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
