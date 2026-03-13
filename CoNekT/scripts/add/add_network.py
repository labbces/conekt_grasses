#!/usr/bin/env python3

import argparse
import json
import sys
from collections import defaultdict
from sqlalchemy import create_engine, select
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--network', required=True)
    parser.add_argument('--species_code', required=True)
    parser.add_argument('--description', required=True)
    parser.add_argument('--hrr_score_threshold', type=int)
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
    NetworkMethod = Base.classes.expression_network_methods
    Network = Base.classes.expression_networks

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        species = session.execute(select(Species).where(Species.code == args.species_code)).scalar_one_or_none()
        if not species:
            raise ValueError(f"Species '{args.species_code}' not found.")
        species_id = species.id

        sequences = session.execute(
            select(Sequence.id, Sequence.name).where(
                Sequence.species_id == species_id,
                Sequence.type == 'protein_coding'
            )
        ).all()
        seq_dict = {s.name.upper(): s.id for s in sequences}

        print(f"Loaded {len(seq_dict)} protein-coding genes.")

        # Check if method already exists
        existing = session.execute(
            select(NetworkMethod).where(NetworkMethod.description == args.description)
        ).scalar_one_or_none()
        if existing:
            raise ValueError(f"Network method '{args.description}' already exists.")

        method = NetworkMethod(
            species_id=species_id,
            description=args.description,
            edge_type="rank",
            hrr_cutoff=args.hrr_score_threshold or 100,
            pcc_cutoff=0.7,
            enable_second_level=False
        )
        session.add(method)
        session.commit()
        session.refresh(method)

        # Parse network file
        network = {}
        scores = defaultdict(lambda: defaultdict(lambda: None))

        with open(args.network) as f:
            for linenr, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    query, hits_str = line.split(' ', 1)
                    query = query.rstrip(':')
                except ValueError:
                    print(f"Skipping malformed line {linenr}: {line}", file=sys.stderr)
                    continue

                network[query] = {
                    "probe": query,
                    "sequence_id": seq_dict.get(query.upper()),
                    "linked_probes": [],
                    "total_count": 0,
                    "method_id": method.id
                }

                for i, h in enumerate(hits_str.split('\t')):
                    try:
                        name, val_str = h.split('(')
                        value = float(val_str.rstrip(')'))
                        if value > 0.7:  # pcc_cutoff
                            network[query]["total_count"] += 1
                            if i < (args.hrr_score_threshold or 100):
                                gene_id = seq_dict.get(name.upper())
                                link = {
                                    "probe_name": name,
                                    "gene_name": name,
                                    "gene_id": gene_id,
                                    "link_score": i,
                                    "link_pcc": value
                                }
                                network[query]["linked_probes"].append(link)
                                scores[query][name] = i
                    except (ValueError, IndexError):
                        continue

        # Compute HRR
        hr_ranks = defaultdict(lambda: defaultdict(int))
        for query, targets in scores.items():
            for target, score in targets.items():
                rev_score = scores[target].get(query)
                if score is not None and rev_score is not None:
                    hr_ranks[query][target] = max(score, rev_score) + 1

        # Build final network JSON
        nodes = []
        for query, data in network.items():
            for link in data["linked_probes"]:
                link["hrr"] = hr_ranks[query].get(link["probe_name"])
            filtered_links = [l for l in data["linked_probes"] if l["hrr"] is not None]
            if filtered_links:
                node = Network(
                    network=json.dumps(filtered_links),
                    probe=data["probe"],
                    sequence_id=data["sequence_id"],
                    method_id=data["method_id"]
                )
                nodes.append(node)

        # Insert in batches
        batch = []
        for node in nodes:
            batch.append(node)
            if len(batch) >= 400:
                session.add_all(batch)
                session.commit()
                batch.clear()
        if batch:
            session.add_all(batch)
            session.commit()

        print(f"✅ Added co-expression network for '{args.species_code}' ({len(nodes)} nodes).")
    finally:
        session.close()

if __name__ == '__main__':
    main()
