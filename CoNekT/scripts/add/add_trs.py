#!/usr/bin/env python3

#Uses CoNekT virtual environment (python3.8)

import getpass
import argparse
from collections import defaultdict

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select
from sqlalchemy import select   


parser = argparse.ArgumentParser(description='Add transcription factors and their associations to the database')
parser.add_argument('--tr_families', type=str, metavar='tr_families.txt',
                    dest='tr_families_file',
                    help='The TXT file with tr families and descriptions',
                    required=False)
parser.add_argument('--tr_associations', type=str, metavar='tr_associations.txt',
                    dest='tr_associations_file',
                    help='The TXT file with gene-to-tr associations',
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
TranscriptionRegulator = Base.classes.transcription_regulator
SequenceTRAssociation = Base.classes.sequence_tr
SequenceTRDomainAssociation = Base.classes.sequence_tr_domain

Session = sessionmaker(bind=engine)
session = Session()

def add_tr_families(filename):
    """
    Populates transcription_regulator table with families and descriptions from a TXT file
    """
    print(f"Adding TR families from {filename}")
    # Optionally clear the table first
    try:
        session.query(TranscriptionRegulator).delete()
        session.commit()
    except Exception as e:
        session.rollback()
        print(e)
    with open(filename, 'r') as fin:
        i = 0
        for line in fin:
            parts = line.strip().split(':')
            if len(parts) == 2:
                family, type_domains = parts[0], parts[1]
                parts2 = type_domains.strip().split(';')
                type = parts2[0].strip()
                tr = TranscriptionRegulator(family=family, type=type)
                session.add(tr)
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
    print(f"Added {i} TR families.")

def add_tr_associations(filename, species_code):
    print(f"Adding TR associations from {filename} for species {species_code}")
    # Find species
    with engine.connect() as conn:
        stmt = select([Species]).where(Species.code == species_code)
        print(species_code, stmt)
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
    # Get all TRs
    with engine.connect() as conn:
        stmt = select([TranscriptionRegulator])
        all_trs = conn.execute(stmt)
        all_trs = all_trs.fetchall()
    gene_hash = {s.name: s for s in all_sequences}
    tr_hash = {tr.family: tr for tr in all_trs}
    associations = []
    gene_tr = defaultdict(list)

    existing_tr_associations = set()
    existing_domain_associations = set()
    with engine.connect() as conn:
        stmt = select([SequenceTRAssociation.sequence_id, SequenceTRAssociation.tr_id])
        result = conn.execute(stmt)
        for row in result:
            existing_tr_associations.add((row.sequence_id, row.tr_id, row.type))

        stmt2 = select([SequenceTRDomainAssociation.sequence_id, SequenceTRDomainAssociation.domain, SequenceTRDomainAssociation.query_start, SequenceTRDomainAssociation.query_end])
        result2 = conn.execute(stmt2)
        for row in result2:
            existing_domain_associations.add((row.sequence_id, row.domain, row.query_start, row.query_end))
    print(existing_tr_associations)

    with open(filename, "r") as f:
        header = f.readline()  # skip header
        for line in f:
            parts = line.strip().split('\t')
            print(parts)
            if len(parts) < 5:
                continue
            gene, family, type, domain, query_start, query_end = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
            gene = gene.rsplit('.', 1)[0] if '.p' in gene else gene
            if gene in gene_hash.keys():
                current_sequence = gene_hash[gene]
                if family in tr_hash.keys():
                    current_tr = tr_hash[family]
                    key = (current_sequence.id, current_tr.id)
                    key2 = (current_sequence.id, domain, int(query_start), int(query_end))
                    if key not in existing_tr_associations:
                        print(f"Adding association for {gene} with TR {family}")
                        association = SequenceTRAssociation(
                            sequence_id=current_sequence.id,
                            tr_id=current_tr.id
                        )
                        session.add(association)
                        existing_tr_associations.add(key)
                    if key2 not in existing_domain_associations:
                        print(f"Adding domain association for {gene} with TR {family}")
                        domain_association = SequenceTRDomainAssociation(
                            sequence_id=current_sequence.id,
                            domain=domain,
                            query_start=int(query_start),
                            query_end=int(query_end)
                        )
                        session.add(domain_association)
                        existing_domain_associations.add(key2)
                    if family not in gene_tr[gene]:
                        gene_tr[gene].append(family)
                else:
                    print(family, "not found in the database.")
            else:
                print("Gene", gene, "not found in the database.")
            if len(associations) > 400:
                try:
                    session.commit()
                    associations = []
                    domain_association = []
                except Exception as e:
                    session.rollback()
                    print(e)
    try:
        session.commit()
    except Exception as e:
        session.rollback()
        print(e)
    print("TR associations added.")

if args.tr_families_file:
    add_tr_families(args.tr_families_file)
if args.tr_associations_file:
    add_tr_associations(args.tr_associations_file, args.species_code)
session.close() 