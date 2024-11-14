#!/usr/bin/env python3

import getpass
import argparse
import psutil

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select

parser = argparse.ArgumentParser(description='Add interproscan results to the database')
parser.add_argument('--interproscan_tsv', type=str, metavar='species_interproscan.tsv',
                    dest='interproscan_file',
                    help='The TSV file from InterProScan results',
                    required=True)
parser.add_argument('--species_code', type=str, metavar='Svi',
                    dest='species_code',
                    help='The CoNekT Grasses species code',
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
    db_password = getpass.getpass("Enter the database password: ")

class InterproDomainParser:
    def __init__(self):
        self.annotation = {}

    def read_interproscan(self, filename):
        with open(filename, "r") as f:
            for line in f:
                parts = line.split('\t')
                if len(parts) > 11:
                    gene = parts[0]
                    domain = {"id": parts[11],
                              "ipr_source_db": parts[3],
                              "start": int(parts[6]),
                              "stop": int(parts[7])}

                    if gene not in self.annotation.keys():
                        self.annotation[gene] = []

                    if domain not in self.annotation[gene]:
                        self.annotation[gene].append(domain)


def print_memory_usage():
    # Get memory usage statistics
    memory = psutil.virtual_memory()

    # Print memory usage
    print(f"Total Memory: {memory.total / (1024.0 ** 3):.2f} GB")
    print(f"Available Memory: {memory.available / (1024.0 ** 3):.2f} GB")
    print(f"Used Memory: {memory.used / (1024.0 ** 3):.2f} GB")
    print(f"Memory Usage Percentage: {memory.percent}%\n")

def add_interpro_from_interproscan(filename, species_code, engine):
        """
        Adds annotation from InterProScan Output (TSV format) to the database

        :param filename: Path to the annotation file
        :param species_code: CoNekT Grasses species code
        :return:
        """

        # Check if species exists in the database
        with engine.connect() as conn:
            stmt = select(Species).where(Species.__table__.c.code == species_code)
            species = conn.execute(stmt).first()

        if not species:
            print(f"Species ({species_code}) not found in the database.")
            exit(1)
        else:
            species_id = species.id

        interpro_parser = InterproDomainParser()

        interpro_parser.read_interproscan(filename)

        gene_hash = {}
        domain_hash = {}

        with engine.connect() as conn:
            stmt = select(Sequence).where(Sequence.__table__.c.species_id == species_id,\
                                          Sequence.__table__.c.type == 'protein_coding')
            all_sequences = conn.execute(stmt).all()
        
        with engine.connect() as conn:
            stmt = select(Interpro)
            all_domains = conn.execute(stmt).all()

        for sequence in all_sequences:
            gene_hash[sequence.name] = sequence

        for domain in all_domains:
            domain_hash[domain.label] = domain

        new_domains = []

        for gene, domains in interpro_parser.annotation.items():
            if gene in gene_hash.keys():
                current_sequence = gene_hash[gene]
                for domain in domains:
                    if domain["id"] in domain_hash.keys():
                        current_domain = domain_hash[domain["id"]]

                        new_domain = {"sequence_id": current_sequence.id,
                                      "interpro_id": current_domain.id,
                                      "ipr_source_db": domain["ipr_source_db"],
                                      "start": domain["start"],
                                      "stop": domain["stop"]}

                        new_domains.append(new_domain)

                        new_domain_obj = SequenceInterproAssociation(**new_domain)

                        session.add(new_domain_obj)

                    else:
                        print(domain["id"], "not found in the database.")
            else:
                print("Gene", gene, "not found in the database.")

            if len(new_domains) > 400:
                session.commit()
                print_memory_usage()
                new_domains = []

        session.commit()
        print_memory_usage()

interproscan_tsv = args.interproscan_file
sps_code = args.species_code
db_admin = args.db_admin
db_name = args.db_name

create_engine_string = "mysql+pymysql://"+db_admin+":"+db_password+"@localhost/"+db_name

engine = create_engine(create_engine_string, echo=True)

# Reflect an existing database into a new model
Base = automap_base()

Base.prepare(engine, reflect=True)

Species = Base.classes.species
Sequence = Base.classes.sequences
SequenceInterproAssociation = Base.classes.sequence_interpro
Interpro = Base.classes.interpro

# Create a Session
Session = sessionmaker(bind=engine)
session = Session()

# Run function to add interproscan results for species
add_interpro_from_interproscan(interproscan_tsv, sps_code, engine)

session.close()