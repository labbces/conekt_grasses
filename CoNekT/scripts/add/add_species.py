#!/usr/bin/env python3

import argparse
import gzip
import operator
import time
from sqlalchemy import create_engine, select
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from crossref.restful import Works

class Fasta:
    def __init__(self):
        self.sequences = {}

    def readfile(self, filename, compressed=False):
        opener = gzip.open if compressed else open
        mode = 'rt' if compressed else 'r'
        with opener(filename, mode) as f:
            name = ''
            seq = []
            for line in f:
                line = line.rstrip()
                if line.startswith('>'):
                    if name:
                        self.sequences[name] = ''.join(seq)
                        seq = []
                    name = line[1:]
                else:
                    seq.append(line)
            if name:
                self.sequences[name] = ''.join(seq)

def add_literature(session, doi):
    Lit = session.get_bind().execute.__self__.class_registry['literature']
    existing = session.execute(select(Lit).where(Lit.doi == doi)).scalar_one_or_none()
    if existing:
        return existing.id

    works = Works()
    info = works.doi(doi)
    author = info['author'][0].get('family') or info['author'][0].get('name', 'Unknown')
    title = info.get('title', [''])[0] if isinstance(info.get('title'), list) else info.get('title', '')
    year = (
        info.get('published-print', {}).get('date-parts', [[None]])[0][0] or
        info.get('published-online', {}).get('date-parts', [[None]])[0][0] or
        info.get('issued', {}).get('date-parts', [[None]])[0][0] or
        0
    )
    new_lit = Lit(
        qtd_author=len(info['author']),
        author_names=author,
        title=title,
        public_year=year,
        doi=doi
    )
    session.add(new_lit)
    session.commit()
    return new_lit.id

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_table', required=True)
    parser.add_argument('--db_admin', required=True)
    parser.add_argument('--db_name', required=True)
    parser.add_argument('--db_password')
    args = parser.parse_args()

    pwd = args.db_password or input("Enter DB password: ")
    engine = create_engine(f"mysql+pymysql://{args.db_admin}:{pwd}@localhost/{args.db_name}")
    Base = automap_base()
    Base.prepare(autoload_with=engine)

    Species = Base.classes.species
    Sequence = Base.classes.sequences
    Lit = Base.classes.literature

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        with open(args.input_table) as f:
            for line in f:
                if line.startswith('#') or not line.strip():
                    continue
                parts = line.strip().split('\t')
                if len(parts) != 7:
                    continue
                name, code, source, version, doi, cds_file, rna_file = parts

                # Skip if already exists
                existing = session.execute(select(Species).where(Species.code == code)).scalar_one_or_none()
                if existing:
                    print(f"Skipping existing species: {code}")
                    continue

                # Add literature if DOI provided
                lit_id = None
                if doi and doi != 'None':
                    try:
                        lit_id = add_literature(session, doi)
                        time.sleep(3)  # Be kind to CrossRef
                    except Exception as e:
                        print(f"Warning: failed to fetch literature for {doi}: {e}")

                # Add species
                species = Species(
                    code=code,
                    name=name,
                    data_type='genome',
                    color="#C7C7C7",
                    highlight="#DEDEDE",
                    description=None,
                    source=source,
                    sequence_count=0,
                    profile_count=0,
                    network_count=0,
                    literature_id=lit_id,
                    genome_version=version
                )
                session.add(species)
                session.commit()
                session.refresh(species)

                # Add CDS sequences
                fasta = Fasta()
                compressed = cds_file.endswith('.gz')
                fasta.readfile(cds_file, compressed=compressed)
                seq_batch = []
                for name, seq in sorted(fasta.sequences.items(), key=operator.itemgetter(0)):
                    seq_batch.append(Sequence(
                        species_id=species.id,
                        name=name,
                        description=None,
                        coding_sequence=seq,
                        type='protein_coding',
                        is_mitochondrial=False,
                        is_chloroplast=False
                    ))
                    if len(seq_batch) >= 400:
                        session.add_all(seq_batch)
                        session.commit()
                        seq_batch.clear()
                if seq_batch:
                    session.add_all(seq_batch)
                    session.commit()

                # Add RNA sequences
                fasta = Fasta()
                compressed = rna_file.endswith('.gz')
                fasta.readfile(rna_file, compressed=compressed)
                seq_batch = []
                for name, seq in sorted(fasta.sequences.items(), key=operator.itemgetter(0)):
                    seq_batch.append(Sequence(
                        species_id=species.id,
                        name=name,
                        description=None,
                        coding_sequence=seq,
                        type='RNA',
                        is_mitochondrial=False,
                        is_chloroplast=False
                    ))
                    if len(seq_batch) >= 400:
                        session.add_all(seq_batch)
                        session.commit()
                        seq_batch.clear()
                if seq_batch:
                    session.add_all(seq_batch)
                    session.commit()

                print(f"✅ Added species {code} ({name}) with {len(fasta.sequences)} RNA sequences.")

    finally:
        session.close()

if __name__ == '__main__':
    main()
