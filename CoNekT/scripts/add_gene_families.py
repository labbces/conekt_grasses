#!/usr/bin/env python3

import argparse
import psutil

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select
from collections import defaultdict

# Create arguments
parser = argparse.ArgumentParser(description='Add gene families to the database')
parser.add_argument('--orthogroups', type=str, metavar='Orthogroups.txt',
                    dest='orthogroups_file',
                    help='The Orthogroups.txt file from OrthoFinder',
                    required=True)
parser.add_argument('--description', type=str, metavar='Description',
                    dest='description',
                    help='Description of the method as it should appear in CoNekT',
                    required=True)

args = parser.parse_args()

# Testing with the following library versions:
# * SQLAlchemy-2.0.23
# * pymysql-1.1.0

def print_memory_usage():
    # Get memory usage statistics
    memory = psutil.virtual_memory()

    # Print memory usage
    print(f"Total Memory: {memory.total / (1024.0 ** 3):.2f} GB")
    print(f"Available Memory: {memory.available / (1024.0 ** 3):.2f} GB")
    print(f"Used Memory: {memory.used / (1024.0 ** 3):.2f} GB")
    print(f"Memory Usage Percentage: {memory.percent}%\n")

def add_family_method(description, engine):
        
        print_memory_usage()

        with engine.connect() as conn:
            stmt = select(GeneFamilyMethod).where(GeneFamilyMethod.__table__.c.method == description)
            method = conn.execute(stmt).first()
            if method:
                print(f"Gene family method '{description}' already exists in the database")
                exit(1)
            print_memory_usage()

        try:
            session.add(GeneFamilyMethod(method=description))
            session.commit()
        except Exception as e:
            session.rollback()
            raise e


def add_families(families, family_members):
        """
        Adds gene families to the database and assigns genes to their designated family

        :param families: list of GeneFamily objects
        :param family_members: dict (keys = gene family name) with lists of members
        """

        for i, f in enumerate(families):
            session.add(f)

            if i > 0 and i % 400 == 0:
                # Commit to DB every 400 records
                try:
                    session.commit()
                    print_memory_usage()
                except Exception as e:
                    session.rollback()
                    quit()

        try:
            # Commit to DB remainder
            session.commit()
            print_memory_usage()
        except Exception as e:
            session.rollback()
            quit()

        for i, f in enumerate(families):
            
            with engine.connect() as conn:
                stmt = select(Sequence).where(Sequence.id.in_(list(family_members[f.name])))
                family_sequences = conn.execute(stmt).all()

            for member in family_sequences:
                association = SequenceFamilyAssociation()
                
                association.sequence_id = member.id
                association.gene_family_id = f.id

                session.add(association)

                if i > 0 and i % 400 == 0:
                    # Commit to DB every 400 records
                    try:
                        session.commit()
                        print_memory_usage()
                    except Exception as e:
                        session.rollback()
                        quit()

            del family_sequences

        try:
            # Commit to DB remainder
            session.commit()
            print_memory_usage()
        except Exception as e:
            session.rollback()
            quit()


def add_families_from_orthofinder(filename, description, engine):
        """
        Add gene families directly from OrthoFinder output (one line with all genes from one family)

        :param filename: The file to load
        :param description: Description of the method to store in the database
        :return the new methods internal ID
        """
        # Create new method for these families
        add_family_method(description, engine)

        with engine.connect() as conn:
            stmt = select(GeneFamilyMethod).where(GeneFamilyMethod.__table__.c.method == description)
            method = conn.execute(stmt).first()
            print_memory_usage()

        gene_hash = {}
        print_memory_usage()

        with engine.connect() as conn:
            stmt = select(Sequence.__table__.c.name, Sequence.__table__.c.id).where(Sequence.__table__.c.type == 'protein_coding')
            all_sequences = conn.execute(stmt).all()
            print_memory_usage()
        
        for sequence in all_sequences:
            gene_hash[sequence.name.lower()] = sequence

        print_memory_usage()
        del all_sequences
        print_memory_usage()

        families = set()
        family_members = defaultdict(set)

        with open(filename, "r") as f_in:
            for line in f_in:
                
                if len(families) >= 2000:
                    # add all families
                    add_families(families, family_members)
                    print_memory_usage()
                    
                    del families
                    del family_members
                    families = set()
                    family_members = defaultdict(set)

                orthofinder_id, *parts = line.strip().split()
                orthofinder_id = orthofinder_id.rstrip(':')

                new_family = GeneFamily(name=orthofinder_id.replace('OG', 'OG_%02d_' % method.id))
                new_family.original_name = orthofinder_id
                new_family.method_id = method.id

                families.add(new_family)

                for p in parts:
                    if p.lower() in gene_hash.keys():
                        family_members[new_family.name].add(gene_hash[p.lower()][1])
                        del gene_hash[p.lower()]

        # add all families
        add_families(families, family_members)
        print_memory_usage()

orthogroups_file = args.orthogroups_file
description = args.description

engine = create_engine("mysql+pymysql://conekt_grasses_admin:E,~5*;{9f{p2VGp^@localhost/conekt_grasses_db", echo=True)

# Reflect an existing database into a new model
Base = automap_base()

# Use the engine to reflect the database
Base.prepare(engine, reflect=True)

GeneFamilyMethod = Base.classes.gene_family_methods
GeneFamily = Base.classes.gene_families
Sequence = Base.classes.sequences
SequenceFamilyAssociation = Base.classes.sequence_family

# Create a Session
Session = sessionmaker(bind=engine)
session = Session()

# Run the function to add the families
add_families_from_orthofinder(orthogroups_file, description, engine)

session.close()