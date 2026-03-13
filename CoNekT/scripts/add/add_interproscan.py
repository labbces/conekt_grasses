#!/usr/bin/env python3

import argparse
from sqlalchemy import create_engine, select
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker

class InterproDomainParser:
    def __init__(self):
        self.annotation = {}

    def read_interproscan(self, filename):
        with open(filename) as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) > 11:
                    gene = parts[0]
                    domain = {
                        "id": parts[11],
                        "ipr_source_db": parts[3],
                        "start": int(parts[6]),
                        "stop": int(parts[7])
                    }
                    if gene not in self.annotation:
                        self.annotation[gene] = []
                    if domain not in self.annotation[gene]:
                        self.annotation[gene].append(domain)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--interproscan_tsv', required=True)
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
    Interpro = Base.classes.interpro
    Assoc = Base.classes.sequence_interpro

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

        interpro_domains = session.execute(select(Interpro)).scalars().all()
        domain_hash = {d.label: d for d in interpro_domains}

        print(f"Loaded {len(gene_hash)} genes and {len(domain_hash)} InterPro domains.")

        parser = InterproDomainParser()
        parser.read_interproscan(args.interproscan_tsv)

        batch = []
        count = 0

        for gene, domains in parser.annotation.items():
            if gene not in gene_hash:
                continue
            seq_id = gene_hash[gene].id
            for dom in domains:
                if dom["id"] in domain_hash:
                    assoc = Assoc(
                        sequence_id=seq_id,
                        interpro_id=domain_hash[dom["id"]].id,
                        ipr_source_db=dom["ipr_source_db"],
                        start=dom["start"],
                        stop=dom["stop"]
                    )
                    batch.append(assoc)
                    count += 1
                    if len(batch) >= 400:
                        session.add_all(batch)
                        session.commit()
                        batch.clear()
                        print(f"Committed {count} InterProScan associations...")

        if batch:
            session.add_all(batch)
            session.commit()

        print(f"✅ Added {count} InterProScan associations for '{args.species_code}'.")
    finally:
        session.close()

if __name__ == '__main__':
    main()
