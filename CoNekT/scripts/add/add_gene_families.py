#!/usr/bin/env python3

import argparse
from collections import defaultdict
from sqlalchemy import create_engine, select
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--orthogroups', required=True)
    parser.add_argument('--description', required=True)
    parser.add_argument('--db_admin', required=True)
    parser.add_argument('--db_name', required=True)
    parser.add_argument('--db_password')
    args = parser.parse_args()

    pwd = args.db_password or input("Enter DB password: ")
    engine = create_engine(f"mysql+pymysql://{args.db_admin}:{pwd}@localhost/{args.db_name}")
    Base = automap_base()
    Base.prepare(autoload_with=engine)

    Method = Base.classes.gene_family_methods
    Family = Base.classes.gene_families
    Sequence = Base.classes.sequences
    Assoc = Base.classes.sequence_family

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Add method
        existing_method = session.execute(select(Method).where(Method.method == args.description)).scalar_one_or_none()
        if existing_method:
            raise ValueError(f"Method '{args.description}' already exists.")
        method = Method(method=args.description)
        session.add(method)
        session.commit()
        session.refresh(method)  # Ensure method.id is available

        # Load all protein-coding sequences
        sequences = session.execute(
            select(Sequence.id, Sequence.name).where(Sequence.type == 'protein_coding')
        ).all()
        gene_hash = {row.name.lower(): row.id for row in sequences}

        print(f"Loaded {len(gene_hash)} protein-coding genes.")

        families = []
        members = defaultdict(set)
        batch_count = 0

        with open(args.orthogroups) as f:
            for line in f:
                if batch_count >= 2000:
                    _commit_families(session, families, members, Family, Assoc)
                    families.clear()
                    members.clear()
                    batch_count = 0

                parts = line.strip().split()
                if not parts:
                    continue
                og_id = parts[0].rstrip(':')
                family = Family(
                    name=og_id.replace('OG', f'OG_{method.id:02d}_'),
                    original_name=og_id,
                    method_id=method.id
                )
                families.append(family)
                for gene in parts[1:]:
                    gene_key = gene.lower()
                    if gene_key in gene_hash:
                        members[family.name].add(gene_hash[gene_key])
                batch_count += 1

        if families:
            _commit_families(session, families, members, Family, Assoc)

        print(f"✅ Added gene families from '{args.orthogroups}'.")

    finally:
        session.close()

def _commit_families(session, families, members, Family, Assoc):
    session.add_all(families)
    session.commit()
    # Refresh to get IDs
    for f in families:
        session.refresh(f)

    associations = []
    for family in families:
        for seq_id in members.get(family.name, []):
            associations.append(Assoc(sequence_id=seq_id, gene_family_id=family.id))
            if len(associations) >= 400:
                session.add_all(associations)
                session.commit()
                associations.clear()
    if associations:
        session.add_all(associations)
        session.commit()

if __name__ == '__main__':
    main()
