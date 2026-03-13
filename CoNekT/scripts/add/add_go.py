#!/usr/bin/env python3

import argparse
from collections import defaultdict
from sqlalchemy import create_engine, select
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--go_tsv', required=True)
    parser.add_argument('--species_code', required=True)
    parser.add_argument('--annotation_source', required=True)
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
    GO = Base.classes.go
    Assoc = Base.classes.sequence_go

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        species = session.execute(select(Species).where(Species.code == args.species_code)).scalar_one_or_none()
        if not species:
            raise ValueError(f"Species '{args.species_code}' not found.")
        species_id = species.id

        sequences = session.execute(
            select(Sequence).where(Sequence.species_id == species_id, Sequence.type == 'protein_coding')
        ).scalars().all()
        gene_hash = {s.name: s for s in sequences}

        go_terms = session.execute(select(GO)).scalars().all()
        go_hash = {g.label: g for g in go_terms}

        print(f"Loaded {len(gene_hash)} genes and {len(go_hash)} GO terms.")

        primary_assoc = defaultdict(set)
        batch = []
        count = 0

        with open(args.go_tsv) as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) < 3:
                    continue
                gene, term, evidence = parts[0], parts[1], parts[2]
                if gene in gene_hash and term in go_hash:
                    assoc = Assoc(
                        sequence_id=gene_hash[gene].id,
                        go_id=go_hash[term].id,
                        evidence=evidence,
                        source=args.annotation_source,
                        predicted=0
                    )
                    batch.append(assoc)
                    primary_assoc[gene].add(term)
                    count += 1
                    if len(batch) >= 400:
                        session.add_all(batch)
                        session.commit()
                        batch.clear()
                        print(f"Committed {count} primary GO associations...")

        if batch:
            session.add_all(batch)
            session.commit()

        # Extended GOs
        extended_count = 0
        batch = []
        for gene, terms in primary_assoc.items():
            new_terms = set()
            for term in terms:
                if term in go_hash:
                    extended = go_hash[term].extended_go
                    if extended:
                        for ext in extended.split(';'):
                            if ext and ext not in terms and ext not in new_terms:
                                new_terms.add(ext)
            for ext_term in new_terms:
                if ext_term in go_hash:
                    assoc = Assoc(
                        sequence_id=gene_hash[gene].id,
                        go_id=go_hash[ext_term].id,
                        evidence=None,
                        source="Extended",
                        predicted=0
                    )
                    batch.append(assoc)
                    extended_count += 1
                    if len(batch) >= 400:
                        session.add_all(batch)
                        session.commit()
                        batch.clear()

        if batch:
            session.add_all(batch)
            session.commit()

        print(f"✅ Added {count} primary + {extended_count} extended GO associations for '{args.species_code}'.")
    finally:
        session.close()

if __name__ == '__main__':
    main()
