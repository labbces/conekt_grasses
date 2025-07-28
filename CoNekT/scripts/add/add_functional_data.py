#!/usr/bin/env python3

import getpass
import argparse
import xml.etree.ElementTree as ET
from copy import deepcopy
import gzip
import sys
import os
import math


from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import delete
import logging







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
parser.add_argument('--cazyme', type=str, metavar='cazyme_database.txt',
                    dest='cazymes_file',
                    help='The cazymes.tsv file to add CAZymes to the database',
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

args = parser.parse_args()

if args.db_password:
    db_password = args.db_password
else:
    db_password = getpass.getpass("Enter the database password: ")




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
    logger.info("______________________________________________________________________")
    logger.info("➡️  Adding InterPro data:")
    # If required empty the table first
    if empty:
        logger.debug("Cleaning 'interpro' table...")
        try:
            session.query(Interpro).delete()
            session.commit()
            logger.debug("✅  Table cleaned successfully.")
        except Exception as e:
            print_log_error(e)
            sys.exit(1)
            

    logger.debug(f"Reading InterPro file: {filename}")
    try:
        interpro_parser = InterProParser()
        interpro_parser.readfile(filename)
        total_entries = len(interpro_parser.domains)
    except Exception as e:
        print_log_error(e)
        sys.exit(1)

    logger.debug(f"Found {total_entries} entries in the file.")

    try:
        for i, domain in enumerate(interpro_parser.domains):
        
            interpro = Interpro(**domain.__dict__)

            session.add(interpro)

            if i % 40 == 0:
                # commit to the db frequently to allow WHOOSHEE's indexing function to work without timing out
                session.commit()
            
            step = 10 ** int(math.log10(total_entries))
            if i % step == 0:
                logger.debug(f"{i}/{total_entries} entries processed and committed...")

    
        session.commit()
        logger.info(f"✅  All {total_entries} entries added to table 'interpro' successfully!")


    except Exception as e:
        session.rollback()
        print_log_error(f"Failed while inserting entry number {i}: {e}")
        sys.exit(1)

    
def add_cazymes_from_table(filename, empty=False):
    """
    Populates CAZYme table with domains and descriptions from the dbCAN2 TXT file

    :param filename: path to TXT file
    :param empty: If True the cazyme table will be cleared before uploading the new domains, default = True

    """
    logger.info("______________________________________________________________________")
    logger.info("➡️  Adding CAZYme data:")
    # If required empty the table first
    if empty:
        try:
            logger.debug("Cleaning 'cazyme' table...")
            with engine.begin() as conn:  
                stmt = delete(CAZYme)
                conn.execute(stmt)
                logger.debug("✅  Table cleaned successfully.")
        except Exception as e:
            print_log_error(e)
            sys.exit(1)
        
    class_dict = {
        'GH':'Glycoside Hydrolase',
        'GT':'GlycosylTransferase',
        'PL':'Polysaccharide Lyase',
        'CE':'Carbohydrate Esterase',
        'AA':'Auxiliary Activitie',
        'CBM':'Carbohydrate-Binding Module'
    }

    logger.debug(f"Reading CAZYmes file: {filename}")
    with open(filename, 'r') as fin:
        i = 0

        try:
            for line in fin:
                parts = line.strip().split('\t')
                if len(parts) == 2:
                    family, cazyme_class, activities = parts[0], '', parts[1]
                        
                    string = ''
                    for char in parts[0]:
                        if char.isalpha():
                            string += char
                    cazyme_class = class_dict[string]

                    cazyme = CAZYme(family=family, cazyme_class=cazyme_class, activities=activities)
                    session.add(cazyme)
                        
                    i += 1
                    if i % 40 == 0:
                        # commit to the db frequently to allow WHOOSHEE's indexing function to work without timing out
                        session.commit()

                    if i % 100 == 0:
                        logger.debug(f"{i} entries processed and committed...")

            session.commit()
            logger.info(f"✅  All {i} entries added to table 'cazyme' successfully!")

        except Exception as e:
            session.rollback()
            print_log_error(f"Failed while inserting entry number {i + 1}: {e}")
            sys.exit(1)


def add_go_from_obo(filename, empty=True, compressed=False):
    """
    Parses GeneOntology's OBO file and adds it to the database

    :param filename: Path to the OBO file to parse
    :param compressed: load data from .gz file if true (default: False)
    :param empty: Empty the database first when true (default: True)
    """
    logger.info("______________________________________________________________________")
    logger.info("➡️  Adding GO data:")
    #If required empty the table first
    if empty:
        try:
            logger.debug("Cleaning 'go' table...")
            with engine.begin() as conn:
                stmt = delete(GO)
                conn.execute(stmt)
            logger.debug("✅  Table cleaned successfully.")
        except Exception as e:
            print_log_error(e)
            sys.exit(1)


    logger.debug(f"Reading GO file: {filename}")

    try:
        obo_parser = OBOParser()
        obo_parser.readfile(filename, compressed=compressed)
        obo_parser.extend_go()
    except Exception as e:
        print_log_error(f"Error reading file: {e}")
        sys.exit(1)


    total_entries = len(obo_parser.terms)
    logger.debug(f"Found {total_entries} entries in the file.")

    try:
        for i, term in enumerate(obo_parser.terms):
            go = GO(label=term.id, name=term.name, description=term.definition,
                    type=term.namespace, obsolete=term.is_obsolete,
                    is_a=";".join(term.is_a), extended_go=";".join(term.extended_go))

            session.add(go)

            if i % 40 == 0:
                # commit to the db frequently to allow WHOOSHEE's indexing function to work without timing out
                session.commit()

            step = 10 ** int(math.log10(total_entries))
            if i % step == 0:
                logger.debug(f"{i}/{total_entries} entries processed and committed...")

        session.commit()
        logger.info(f"✅  All {total_entries} entries added to table 'go' successfully!")
        

    except Exception as e:
        session.rollback()  
        print_log_error(f"Failed while inserting entry {term.id}: {e}")
        sys.exit(1)




def setup_logger(log_dir="logs_populate", base_filename="functional data", DBverbose=False, PYverbose=True):
    """
    Sets up the application's logging system with support for both file and console output.

    Creates a logger with separate handlers for info and error messages, writing them to 
    distinct files and displaying them in the console. Also allows enabling or disabling 
    SQLAlchemy engine log propagation.

    :param log_dir: Directory where the log files will be saved (default: "logs_populate")
    :param base_filename: Base name for the generated log files (default: "functional data")
    :param DBverbose: If True, enables SQLAlchemy engine logs to propagate to the console (default: False)
    :return: Configured logger object
    """

    # Set SQLAlchemy logger level
    sqla_logger = logging.getLogger('sqlalchemy.engine')
    sqla_logger.setLevel(logging.INFO)
    sqla_logger.propagate = DBverbose 

    #creates log dir
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger()
    level = logging.DEBUG if PYverbose else logging.INFO
    logger.setLevel(level)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    log_file_base = os.path.join(log_dir, base_filename)
    stdout_log_path = f"{log_file_base}.o.log"
    stderr_log_path = f"{log_file_base}.e.log"

    # File handlers
    file_info_handler = logging.FileHandler(stdout_log_path, mode='w', encoding='utf-8')
    file_info_handler.setLevel(level)
    file_info_handler.setFormatter(formatter)

    file_error_handler = logging.FileHandler(stderr_log_path, mode='w', encoding='utf-8')
    file_error_handler.setLevel(logging.ERROR)
    file_error_handler.setFormatter(formatter)

    # Handlers para console
    console_info_handler = logging.StreamHandler(sys.stdout)
    console_info_handler.setLevel(level)
    console_info_handler.setFormatter(formatter)

    console_error_handler = logging.StreamHandler(sys.stderr)
    console_error_handler.setLevel(logging.ERROR)
    console_error_handler.setFormatter(formatter)

    if not logger.hasHandlers():
        logger.addHandler(file_info_handler)
        logger.addHandler(file_error_handler)
        logger.addHandler(console_info_handler)
        logger.addHandler(console_error_handler)

    return logger



def print_log_error(message):
    """
    Logs an error message and a follow-up instruction to abort the operation.
    :param message: Error message to log
    """
    logger.error(f'❌ {message}')
    logger.error("OPERATION ABORTED. Fix the issue and run the script again.")



def str2bool(v):
    """
    Converts a string or value to a boolean.
    :param v: The input value to convert to boolean
    :return: Boolean value (True or False)
    """
    if isinstance(v, bool):
        return v
    val = str(v).strip().lower()
    if val in ('yes', 'true', 't', '1'):
        return True
    elif val in ('no', 'false', 'f', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError(f'Boolean value expected, got "{v}"')



try:
    thisFileName = os.path.basename(__file__)

    interpro_file = ''
    go_file = ''
    cazymes_file = ''

    db_admin = args.db_admin
    db_name = args.db_name
    interpro_file = args.interpro_file
    go_file = args.go_file
    cazymes_file = args.cazymes_file


    #log variables
    log_dir = args.log_dir  #log dir path
    log_file_name = "functional_data"   #log file names
    db_verbose = str2bool(args.db_verbose)
    py_verbose = str2bool(args.py_verbose)
    logger = setup_logger(log_dir=log_dir, base_filename=log_file_name, DBverbose=db_verbose, PYverbose=py_verbose)
    

    functional_data_count = 0

    if cazymes_file:
        functional_data_count+=1

    if interpro_file:
        functional_data_count+=1

    if go_file:
        functional_data_count+=1

    if functional_data_count == 0:
        print_log_error("Must add at least one type of functional data (e.g., --interpro_xml) to the database!")
        sys.exit(1)

    create_engine_string = "mysql+pymysql://"+db_admin+":"+db_password+"@localhost/"+db_name

    engine = create_engine(create_engine_string, echo=False)

    # Reflect an existing database into a new model
    Base = automap_base()

    # Use the engine to reflect the database
    Base.prepare(engine, reflect=True)

    Interpro = Base.classes.interpro
    GO = Base.classes.go
    CAZYme = Base.classes.cazyme

    # Create a Session
    Session = sessionmaker(bind=engine)
    session = Session()

    # Run the functional data to CoNekT Grasses
    if interpro_file:
        add_interpro_from_xml(interpro_file)

    if go_file:
        add_go_from_obo(go_file)

    if cazymes_file:
        add_cazymes_from_table(cazymes_file)

    session.close()

except Exception as e:
    print_log_error(e)
    logger.info(f" ---- ❌ An error occurred while executing {thisFileName}. Please fix the issue and rerun the script. ❌ ---- ")
    sys.exit(1)



logger.info(f" ---- ✅ SUCCESS: All operations from {thisFileName} finished without errors! ✅ ---- ")





