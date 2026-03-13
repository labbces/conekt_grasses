#!/usr/bin/env python3

import argparse
import os
from sqlalchemy import create_engine, select, delete
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plant_ontology')
    parser.add_argument('--plant_e_c_ontology')
    parser.add_argument('--db_admin', required=True)
    parser.add_argument('--db_name', required=True)
    parser.add_argument('--db_password')
    args = parser.parse_args()

    if not (args.plant_ontology or args.plant_e_c_ontology):
        raise ValueError("At least one ontology file must be provided.")

    pwd = args.db_password or input("Enter DB password: ")
    engine = create_engine(f"mysql+pymysql://{args.db_admin}:{pwd}@localhost/{args.db_name}")
    Base = automap_base()
    Base.prepare(autoload_with=engine)

    PO = Base.classes.plant_ontology
    PECO = Base.classes.plant_experimental_conditions_ontology

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Plant Ontology
        if args.plant_ontology:
            if os.path.getsize(args.plant_ontology) > 0:
                session.execute(delete(PO))
                batch = []
                with open(args.plant_ontology) as f:
                    for line in f:
                        if line.startswith('PO:'):
                            parts = line.strip().split('\t')
                            if len(parts) >= 3:
                                po_id, po_name, po_def = parts[0], parts[1], parts[2]
                                batch.append(PO(
                                    po_term=po_id,
                                    po_class=po_name,
                                    po_annotation=po_def
                                ))
                                if len(batch) >= 40:
                                    session.add_all(batch)
                                    session.commit()
                                    batch.clear()
                if batch:
                    session.add_all(batch)
                    session.commit()
                print(f"✅ Loaded Plant Ontology from {args.plant_ontology}.")

        # PECO
        if args.plant_e_c_ontology:
            if os.path.getsize(args.plant_e_c_ontology) > 0:
                session.execute(delete(PECO))
                batch = []
                with open(args.plant_e_c_ontology) as f:
                    next(f)  # skip header
                    for line in f:
                        if line.startswith('PECO:'):
                            parts = line.strip().split('\t')
                            if len(parts) >= 3:
                                peco_id, peco_name, peco_def = parts[0], parts[1], parts[2]
                                batch.append(PECO(
                                    peco_term=peco_id,
                                    peco_class=peco_name,
                                    peco_annotation=peco_def
                                ))
                                if len(batch) >= 40:
                                    session.add_all(batch)
                                    session.commit()
                                    batch.clear()
                if batch:
                    session.add_all(batch)
                    session.commit()
                print(f"✅ Loaded PECO from {args.plant_e_c_ontology}.")

    finally:
        session.close()

if __name__ == '__main__':
    main()
