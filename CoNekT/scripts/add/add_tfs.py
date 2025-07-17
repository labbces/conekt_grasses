#!/usr/bin/env python3

import getpass
import argparse
from collections import defaultdict

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select
from sqlalchemy import select   


parser = argparse.ArgumentParser(description='Add transcription factors and their associations to the database')
parser.add_argument('--tf_families', type=str, metavar='tf_families.txt',
                    dest='tf_families_file',
                    help='The TXT file with TF families and descriptions',
                    required=False)
parser.add_argument('--tf_associations', type=str, metavar='tf_associations.txt',
                    dest='tf_associations_file',
                    help='The TXT file with gene-to-TF associations',
                    required=False)
parser.add_argument('--species_code', type=str, metavar='Svi',
                    dest='species_code',
                    help='The CoNekT Grasses species code',
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

args = parser.parse_args()

if args.db_password:
    db_password = args.db_password
else:
    db_password = getpass.getpass("Enter the database password: ")

# Set up SQLAlchemy automap
create_engine_string = "mysql+pymysql://" + args.db_admin + ":" + db_password + "@localhost/" + args.db_name
engine = create_engine(create_engine_string, echo=True)
Base = automap_base()
Base.prepare(engine, reflect=True)

Species = Base.classes.species
Sequence = Base.classes.sequences
TranscriptionFactor = Base.classes.transcription_factor
SequenceTFAssociation = Base.classes.sequence_tf

Session = sessionmaker(bind=engine)
session = Session()

def add_tf_families(filename):
    """
    Populates transcription_factor table with families and descriptions from a TXT file
    """
    print(f"Adding TF families from {filename}")
    # Optionally clear the table first
    try:
        session.query(TranscriptionFactor).delete()
        session.commit()
    except Exception as e:
        session.rollback()
        print(e)
    with open(filename, 'r') as fin:
        i = 0
        for line in fin:
            parts = line.strip().split('\t')
            if len(parts) == 2:
                family, description = parts[0], parts[1]
                tf = TranscriptionFactor(family=family, type=None, description=description)
                session.add(tf)
                i += 1
            if i % 40 == 0:
                try:
                    session.commit()
                except Exception as e:
                    session.rollback()
                    print(e)
    try:
        session.commit()
    except Exception as e:
        session.rollback()
        print(e)
    print(f"Added {i} TF families.")

def add_tf_associations(filename, species_code):
    print(f"Adding TF associations from {filename} for species {species_code}")
    # Find species
    with engine.connect() as conn:
        stmt = select([Species]).where(Species.code == species_code)
        species = conn.execute(stmt).first()
    if not species:
        print(f"Species ({species_code}) not found in the database.")
        exit(1)
    species_id = species.id
    # Get all sequences for this species
    with engine.connect() as conn:
        stmt = select([Sequence]).where((Sequence.species_id == species_id) & (Sequence.type == 'protein_coding'))

        all_sequences = conn.execute(stmt)
        print(f"Found {all_sequences.rowcount} sequences for species {species_code}.")
        all_sequences = all_sequences.fetchall()
        print(f"Sequences fetched: {len(all_sequences)}, {all_sequences[0].name if all_sequences else 'No sequences'}")
    # Get all TFs
    with engine.connect() as conn:
        stmt = select([TranscriptionFactor])
        all_tfs = conn.execute(stmt)
        all_tfs = all_tfs.fetchall()
    gene_hash = {s.name: s for s in all_sequences}
    tf_hash = {tf.family: tf for tf in all_tfs}
    associations = []
    gene_tf = defaultdict(list)
    with open(filename, "r") as f:
        header = f.readline()  # skip header
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) < 5:
                continue
            gene, family, type, query_start, query_end = parts[0], parts[1], parts[2], parts[3], parts[4]
            gene = gene.rsplit('.', 1)[0] if '.p' in gene else gene
            if gene in gene_hash.keys():
                current_sequence = gene_hash[gene]
                if family in tf_hash.keys():
                    current_tf = tf_hash[family]
                    association = SequenceTFAssociation(
                        sequence_id=current_sequence.id,
                        tf_id=current_tf.id,
                        query_start=int(query_start),
                        query_end=int(query_end)
                    )
                    session.add(association)
                    if family not in gene_tf[gene]:
                        gene_tf[gene].append(family)
                else:
                    print(family, "not found in the database.")
            else:
                print("Gene", gene, "not found in the database.")
            if len(associations) > 400:
                try:
                    session.commit()
                    associations = []
                except Exception as e:
                    session.rollback()
                    print(e)
    try:
        session.commit()
    except Exception as e:
        session.rollback()
        print(e)
    print("TF associations added.")

if args.tf_families_file:
    add_tf_families(args.tf_families_file)
if args.tf_associations_file:
    add_tf_associations(args.tf_associations_file, args.species_code)
session.close() 