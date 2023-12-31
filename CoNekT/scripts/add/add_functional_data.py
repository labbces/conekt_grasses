#!/usr/bin/env python3

import argparse
import xml.etree.ElementTree as ET
from copy import deepcopy
import gzip


from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import delete

# Create arguments
parser = argparse.ArgumentParser(description='Add functional data to the database')
parser.add_argument('--interpro_xml', type=str, metavar='interpro.xml',
                    dest='interpro_file',
                    help='The interpro.xml file from InterPro',
                    required=False)
parser.add_argument('--gene_ontology_obo', type=str, metavar='go.obo',
                    dest='go_file',
                    help='The go.obo file from Gene Ontology',
                    required=False)
'''
TODO: add CAZyme support
parser.add_argument('--cazyme', type=str, metavar='cazyme_database.txt',
                    dest='cazymes_file',
                    help='The cazymes.tsv file to add CAZymes to the database',
                    required=False)
'''
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


class OboEntry:
    """
    Class to store data for a single entry in an OBO file
    """
    def __init__(self):
        self.id = ''
        self.name = ''
        self.namespace = ''
        self.definition = ''
        self.is_a = []
        self.synonym = []
        self.alt_id = []
        self.extended_go = []
        self.is_obsolete = False

    def set_id(self, term_id):
        self.id = term_id

    def set_name(self, name):
        self.name = name

    def set_namespace(self, namespace):
        self.namespace = namespace

    def set_definition(self, definition):
        self.definition = definition

    def set_extended_go(self, parents):
        self.extended_go = parents

    def add_is_a(self, label):
        self.is_a.append(label)

    def add_synonym(self, label):
        self.synonym.append(label)

    def add_alt_id(self, label):
        self.alt_id.append(label)

    def make_obsolete(self):
        self.is_obsolete = True

    def process(self, key, value):
        """
        function to process new data for the current entry from the OBO file
        """
        if key == "id":
            self.set_id(value)
        elif key == "name":
            self.set_name(value)
        elif key == "namespace":
            self.set_namespace(value)
        elif key == "def":
            self.set_definition(value)
        elif key == "is_a":
            parts = value.split()
            self.add_is_a(parts[0])
        elif key == "synonym":
            self.add_synonym(value)
        elif key == "alt_id":
            self.add_alt_id(value)
        elif key == "is_obsolete" and value == "true":
            self.make_obsolete()

    def print(self):
        """
        print term to terminal
        """
        print("ID:\t\t" + self.id)
        print("Name:\t\t" + self.name)
        print("Namespace:\t" + self.namespace)
        print("Definition:\t" + self.definition)
        print("is_a: " + str(self.is_a))
        print("extended_parents: " + str(self.extended_go))

        if self.is_obsolete:
            print("OBSOLETE")


class OBOParser:
    """
    Reads the specified obo file
    """
    def __init__(self):
        self.terms = []

    def print(self):
        """
        prints all the terms to the terminal
        """
        for term in self.terms:
            term.print()

    def readfile(self, filename, compressed=False):
        """
        Reads an OBO file (from filename) and stores the terms as OBOEntry objects
        """
        self.terms = []

        if compressed:
            load = gzip.open
            load_type = 'rt'
        else:
            load = open
            load_type = 'r'

        with load(filename, load_type) as f:
            current_term = None

            for line in f:
                line = line.strip()
                # Skip empty
                if not line:
                    continue

                if line == "[Term]":
                    if current_term:
                        self.terms.append(current_term)
                    current_term = OboEntry()
                elif line == "[Typedef]":
                    # Skip [Typedef sections]
                    if current_term:
                        self.terms.append(current_term)
                    current_term = None
                else:
                    # Inside a [Term] environment
                    if current_term is None:
                        continue

                    key, sep, val = line.partition(":")
                    key = key.strip()
                    val = val.strip()
                    current_term.process(key, val)

            if current_term:
                self.terms.append(current_term)

    def extend_go(self):
        """
        Run this after loading the OBO file to fill the extended GO table (all parental terms of the label).
        """
        hashed_terms = {}

        for term in self.terms:
            hashed_terms[term.id] = term

        for term in self.terms:
            extended_go = deepcopy(term.is_a)

            found_new = True

            while found_new:
                found_new = False
                for parent_term in extended_go:
                    new_gos = hashed_terms[parent_term].is_a
                    for new_go in new_gos:
                        if new_go not in extended_go:
                            found_new = True
                            extended_go.append(new_go)

            term.set_extended_go(extended_go)


class InterPro:
    def __init__(self):
        self.label = ''
        self.description = ''

    def set_label(self, label):
        self.label = label

    def set_description(self, description):
        self.description = description

    def print(self):
        print(self.label, self.description)


class InterProParser:
    """
    reads the specified InterPro
    """
    def __init__(self):
        self.domains = []

    def print(self):
        for domain in self.domains:
            domain.print()

    def readfile(self, filename):
        """
        function that reads the file and stores the data in memory
        """
        e = ET.parse(filename).getroot()

        for domain in e.findall('interpro'):
            new_domain = InterPro()

            new_domain.set_label(domain.get('id'))
            new_domain.set_description(domain.get('short_name'))

            self.domains.append(new_domain)

def add_interpro_from_xml(filename, empty=True):
    """
    Populates interpro table with domains and descriptions from the official website's XML file

    :param filename: path to XML file
    :param empty: If True the interpro table will be cleared before uploading the new domains, default = True
    """
    # If required empty the table first
    if empty:
        with engine.connect() as conn:
            stmt = delete(Interpro)
            conn.execute(stmt)

    interpro_parser = InterProParser()

    interpro_parser.readfile(filename)

    for i, domain in enumerate(interpro_parser.domains):
        interpro = Interpro(**domain.__dict__)

        session.add(interpro)

        if i % 40 == 0:
            # commit to the db frequently to allow WHOOSHEE's indexing function to work without timing out
            session.commit()

    session.commit()

def add_go_from_obo(filename, empty=True, compressed=False):
    """
    Parses GeneOntology's OBO file and adds it to the database

    :param filename: Path to the OBO file to parse
    :param compressed: load data from .gz file if true (default: False)
    :param empty: Empty the database first when true (default: True)
    """
    # If required empty the table first
    if empty:
        with engine.connect() as conn:
            stmt = delete(GO)
            conn.execute(stmt)

    obo_parser = OBOParser()
    obo_parser.readfile(filename, compressed=compressed)

    obo_parser.extend_go()

    for i, term in enumerate(obo_parser.terms):
        go = GO(label=term.id, name=term.name, description=term.definition,
                type=term.namespace, obsolete=term.is_obsolete,
                is_a=";".join(term.is_a), extended_go=";".join(term.extended_go))

        session.add(go)

        if i % 40 == 0:
            # commit to the db frequently to allow WHOOSHEE's indexing function to work without timing out
            session.commit()

    session.commit()


interpro_file = ''
go_file = ''

db_admin = args.db_admin
db_name = args.db_name
interpro_file = args.interpro_file
go_file = args.go_file

functional_data_count = 0

if interpro_file:
    functional_data_count+=1

if go_file:
    functional_data_count+=1

if functional_data_count == 0:
    print("Must add at least one type of functional data (e.g., --interpro_xml)\
          to the database!")
    exit(1)

create_engine_string = "mysql+pymysql://"+db_admin+":"+db_password+"@localhost/"+db_name

engine = create_engine(create_engine_string, echo=True)

# Reflect an existing database into a new model
Base = automap_base()

# Use the engine to reflect the database
Base.prepare(engine, reflect=True)

Interpro = Base.classes.interpro
GO = Base.classes.go

# Create a Session
Session = sessionmaker(bind=engine)
session = Session()

# Run the functional data to CoNekT Grasses
if interpro_file:
    add_interpro_from_xml(interpro_file)

if go_file:
    add_go_from_obo(go_file)

session.close()