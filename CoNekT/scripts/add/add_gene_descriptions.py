#!/usr/bin/env python3

import argparse
from sqlalchemy import create_engine, select, update
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--species_code', required=True)
    parser.add_argument('--gene_descriptions', required=True)
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

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        species = session.execute(select(Species).where(Species.code == args.species_code)).scalar_one_or_none()
        if not species:
            raise ValueError(f"Species '{args.species_code}' not found.")

        sequences = session.execute(
            select(Sequence).where(Sequence.species_id == species.id, Sequence.type == 'protein_coding')
        ).scalars().all()
        seq_dict = {s.name: s for s in sequences}

        updated = 0
        with open(args.gene_descriptions) as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) < 2:
                    continue
                gene, desc = parts[0], '\t'.join(parts[1:])
                if gene in seq_dict:
                    seq_dict[gene].description = desc
                    updated += 1

        session.commit()
        print(f"✅ Updated descriptions for {updated} genes in '{args.species_code}'.")
    finally:
        session.close()

if __name__ == '__main__':
    main()
