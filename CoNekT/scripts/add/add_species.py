#!/usr/bin/env python3

import argparse
import psutil
import sys
import gzip
import operator

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select

from crossref.restful import Works

parser = argparse.ArgumentParser(description='Add species to the database')
parser.add_argument('--input_table', type=str, metavar='conekt_species.tsv',
                    dest='species_file',
                    help='The TSV file with the species information',
                    required=True)
parser.add_argument('--db_admin', type=str, metavar='DB admin',
                    dest='db_admin',
                    help='The database admin user',
                    required=True)
parser.add_argument('--db_name', type=str, metavar='DB name',
                    dest='db_name',
                    help='The database name',
                    required=True)

args = parser.parse_args()

db_password = input("Enter the database password: ")


class Fasta:
    def __init__(self):
        self.sequences = {}

    def remove_subset(self, length):
        """
        Removes a set of sequences and returns those as a subset

        :param length: number of sequences to remove
        :return: Fasta object with the sequences removed from the current one
        """
        output = Fasta()
        keys = list(self.sequences.keys())
        output.sequences = {k: self.sequences[k] for k in keys[:length]}

        self.sequences = {k: self.sequences[k] for k in keys[length:]}

        return output

    def readfile(self, filename, compressed=False, verbose=False):
        """
        Reads a fasta file to the dictionary

        :param filename: file to read
        :param compressed: set to true if reading form a gzipped file
        :param verbose: set to true to get extra debug information printed to STDERR
        """
        if verbose:
            print("Reading FASTA file:" + filename + "...", file=sys.stderr)

        # Initialize variables
        name = ''
        sequence = []
        count = 1

        # open file
        if compressed:
            f = gzip.open(filename, 'rt')
        else:
            f = open(filename, 'r')

        for line in f:
            line = line.rstrip()
            if line.startswith(">"):
                # ignore if first
                if not name == '':
                    self.sequences[name] = ''.join(sequence)
                    count += 1
                name = line.lstrip('>')
                sequence = []
            else:
                sequence.append(line)

        # add last gene
        self.sequences[name] = ''.join(sequence)

        f.close()
        if verbose:
            print("Done! (found ", count, " sequences)", file=sys.stderr)

    def writefile(self, filename):
        """
        writes the sequences back to a fasta file

        :param filename: file to write to
        """
        with open(filename, 'w') as f:
            for k, v in self.sequences.items():
                print(">" + k, file=f)
                print(v, file=f)

def print_memory_usage():
    # Get memory usage statistics
    memory = psutil.virtual_memory()

    # Print memory usage
    print(f"Total Memory: {memory.total / (1024.0 ** 3):.2f} GB")
    print(f"Available Memory: {memory.available / (1024.0 ** 3):.2f} GB")
    print(f"Used Memory: {memory.used / (1024.0 ** 3):.2f} GB")
    print(f"Memory Usage Percentage: {memory.percent}%\n")

def add_literature(doi, engine):

        works = Works()
        # verify if DOI already exists in DB, if not, collect data
        literature_info = works.doi(doi)

        qtd_author = len(literature_info['author'])
        
        if 'family' in literature_info['author'][0].keys():
            author_names = literature_info['author'][0]['family']
        else:
            author_names = literature_info['author'][0]['name']

        title = literature_info['title']
        
        if 'published-print' in literature_info.keys():
            public_year = literature_info['published-print']['date-parts'][0][0]
        elif 'published-online' in literature_info.keys():
            public_year = literature_info['published-online']['date-parts'][0][0]
        else:
            public_year = literature_info['issued']['date-parts'][0][0]

        new_literature = LiteratureItem(qtd_author=qtd_author,
                                        author_names=author_names,
                                        title=title,
                                        public_year=public_year,
                                        doi=doi)
    
        with engine.connect() as conn:
            stmt = select(LiteratureItem).where(LiteratureItem.__table__.c.doi == doi)
            literature = conn.execute(stmt).first()

        # literature is not in the DB yet, add it
        if not literature:
            session.add(new_literature)
            session.commit()

            return new_literature.id
        else:
            return literature.id


def add_species(code, name, engine, data_type='genome',
            color="#C7C7C7", highlight="#DEDEDE", description=None,
            source=None, literature_id=None, genome_version=None):

        new_species = Species(code=code,
                              name=name,
                              data_type=data_type,
                              color=color,
                              highlight=highlight,
                              description=description,
                              source=source,
                              sequence_count = 0,
                              profile_count = 0,
                              network_count = 0,
                              literature_id=literature_id,
                              genome_version=genome_version)

        with engine.connect() as conn:
            stmt = select(Species).where(Species.__table__.c.code == code)
            species = conn.execute(stmt).first()

        # species is not in the DB yet, add it
        if not species:
            session.add(new_species)
            session.commit()

            return new_species.id
        else:
            return species.id


def add_from_fasta(filename, species_id, compressed=False, sequence_type='protein_coding'):
    fasta_data = Fasta()
    fasta_data.readfile(filename, compressed=compressed)

    new_sequences = []

    # Loop over sequences, sorted by name (key here) and add to db
    for name, sequence in sorted(fasta_data.sequences.items(), key=operator.itemgetter(0)):
        new_sequence = {"species_id": species_id,
                        "name": name,
                        "description": None,
                        "coding_sequence": sequence,
                        "type": sequence_type,
                        "is_mitochondrial": False,
                        "is_chloroplast": False}

        new_sequences.append(new_sequence)

        new_sequence_obj = Sequence(**new_sequence)

        session.add(new_sequence_obj)

        # add 400 sequences at the time
        if len(new_sequences) > 400:
            session.commit()
            print_memory_usage()
            new_sequences = []

    # add the last set of sequences
    session.commit()
    print_memory_usage()

    return len(fasta_data.sequences.keys())


db_admin = args.db_admin
db_name = args.db_name

create_engine_string = "mysql+pymysql://"+db_admin+":"+db_password+"@localhost/"+db_name

engine = create_engine(create_engine_string, echo=True)

# Reflect an existing database into a new model
Base = automap_base()

Base.prepare(engine, reflect=True)

Species = Base.classes.species
Sequence = Base.classes.sequences
LiteratureItem = Base.classes.literature

# Create a Session
Session = sessionmaker(bind=engine)
session = Session()

# Loop over species file and add to DB
species_file = open(args.species_file, 'r')

for line in species_file:
    if line.startswith("#"):
        continue
    line = line.rstrip()
    name, code, genome_source, genome_version, doi, cds_file, rna_file = line.split("\t")

    # skip if species exists
    with engine.connect() as conn:
        stmt = select(Species).where(Species.__table__.c.code == code)
        species = conn.execute(stmt).first()
    
    if species:
        continue

    # add literature
    if doi:
        literature_id = add_literature(doi, engine)
    else:
        literature_id = None

    # add species
    species_id = add_species(code, name, engine, source=genome_source, literature_id=literature_id, genome_version=genome_version)

    # add sequences
    num_seq_added_cds = add_from_fasta(cds_file, species_id, sequence_type='protein_coding')
    num_seq_added_rna = add_from_fasta(rna_file, species_id, sequence_type='RNA')

    print(f"Added {num_seq_added_cds} CDS and {num_seq_added_rna} RNA sequences for {name} ({code})")


session.close()