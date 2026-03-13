#!/usr/bin/env python3

import argparse
from collections import defaultdict
from sqlalchemy import create_engine, select
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker

def main():
    parser = argparse.ArgumentParser(description='Add CAZymes results to the database')
    parser.add_argument('--cazyme_tsv', required=True)
    parser.add_argument('--species_code', required=True)
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
    CAZYme = Base.classes.cazyme
    Assoc = Base.classes.sequence_cazyme

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        species = session.execute(select(Species).where(Species.code == args.species_code)).scalar_one_or_none()
        if not species:
            raise ValueError(f"Species '{args.species_code}' not found in database.")

        sequences = session.execute(
            select(Sequence).where(Sequence.species_id == species.id, Sequence.type == 'protein_coding')
        ).scalars().all()
        gene_hash = {s.name: s for s in sequences}

        cazymes = session.execute(select(CAZYme)).scalars().all()
        cazyme_hash = {c.family: c for c in cazymes}

        print(f"Loaded {len(gene_hash)} genes and {len(cazyme_hash)} CAZy families.")

        batch = []
        count = 0

        with open(args.cazyme_tsv) as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) < 7:
                    continue
                term, hmm_len, gene, q_len, e_val, start, end = parts[:7]
                term = term.replace('.hmm', '')
                if gene in gene_hash and term in cazyme_hash:
                    assoc = Assoc(
                        sequence_id=gene_hash[gene].id,
                        cazyme_id=cazyme_hash[term].id,
                        hmm_length=hmm_len,
                        query_length=q_len,
                        e_value=e_val,
                        query_start=start,
                        query_end=end
                    )
                    batch.append(assoc)
                    count += 1
                    if len(batch) >= 400:
                        session.add_all(batch)
                        session.commit()
                        batch.clear()
                        print(f"Committed {count} associations...")

        if batch:
            session.add_all(batch)
            session.commit()

        print(f"✅ Successfully added {count} CAZyme associations for '{args.species_code}'.")
    finally:
        session.close()

if __name__ == '__main__':
    main()
