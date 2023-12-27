#!/usr/bin/env python3

import argparse
import psutil
import json
from collections import defaultdict

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select

# Create arguments
parser = argparse.ArgumentParser(description='Add network to the database')
parser.add_argument('--network', type=str, metavar='network.txt',
                    dest='network_file',
                    help='The network.txt file from LSTrAP',
                    required=True)
parser.add_argument('--species_code', type=str, metavar='Svi',
                    dest='species_code',
                    help='The CoNekT Grasses species code',
                    required=True)
parser.add_argument('--description', type=str, metavar='Description',
                    dest='description',
                    help='Description of the network as it should appear in CoNekT',
                    required=True)
parser.add_argument('--db_admin', type=str, metavar='DB admin',
                    dest='db_admin',
                    help='The database admin user',
                    required=True)
parser.add_argument('--db_name', type=str, metavar='DB name',
                    dest='db_name',
                    help='The database name',
                    required=True)

args = parser.parse_args()

db_password = input("Enter the database password: ")

def print_memory_usage():
    # Get memory usage statistics
    memory = psutil.virtual_memory()

    # Print memory usage
    print(f"Total Memory: {memory.total / (1024.0 ** 3):.2f} GB")
    print(f"Available Memory: {memory.available / (1024.0 ** 3):.2f} GB")
    print(f"Used Memory: {memory.used / (1024.0 ** 3):.2f} GB")
    print(f"Memory Usage Percentage: {memory.percent}%\n")

def read_expression_network_lstrap(network_file, species_code, description, engine, score_type="rank",
                                       pcc_cutoff=0.7, limit=40, enable_second_level=False):
    """
    Reads a network from disk, generated using LSTrAP, determing hrr scores for each pair and store things in the
    DB.

    :param network_file: path to input file
    :param species_id: species the data is from
    :param description: description to add to the db for this network
    :param score_type: which scores are used, default = "rank"
    :param pcc_cutoff: pcc threshold, pairs with a score below this will be ignored
    :param limit: hrr score threshold, pairs with a score above this will be ignored
    :param enable_second_level: include second level neighborhood in the database (only to be used for sparse networks)
    :return: internal ID of the new network
    """

    with engine.connect() as conn:
        stmt = select(Species).where(Species.__table__.c.code == species_code)
        species_id = conn.execute(stmt).first().id
    
    if not species_id:
        print(f'Species not found in database: {species_code}')
        exit(1)

    # build conversion table for sequences
    with engine.connect() as conn:
            stmt = select(Sequence).where(Sequence.__table__.c.species_id == species_id,\
                                          Sequence.__table__.c.type == 'protein_coding')
            sequences = conn.execute(stmt).all()

    sequence_dict = {} # key = sequence name uppercase, value internal id
    for s in sequences:
        sequence_dict[s.name.upper()] = s.id

    # Add network method first
    new_network_method = ExpressionNetworkMethod(species_id, description, score_type)
    new_network_method.hrr_cutoff = limit
    new_network_method.pcc_cutoff = pcc_cutoff
    new_network_method.enable_second_level = enable_second_level

    with engine.connect() as conn:
        stmt = select(ExpressionNetworkMethod).where(ExpressionNetworkMethod.__table__.c.description == description)
        network_method = conn.execute(stmt).first()
        if not network_method:
            session.add(new_network_method)
            session.commit()
        else:
            print(f'Network method already exists in database: {description}')
            exit(1)

    network = {}
    scores = defaultdict(lambda: defaultdict(lambda: None)) # Score for non-existing pairs will be None

    with open(network_file) as fin:
        for linenr, line in enumerate(fin):
            try:
                query, hits = line.strip().split(' ')
                query = query.replace(':', '')
            except ValueError:
                print("Error parsing line %d: \"%s\"" % (linenr, line))
                # skip this line and continue
                continue

            network[query] = {
                "probe": query,
                "sequence_id": sequence_dict[query.upper()] if query.upper() in sequence_dict.keys() else None,
                "linked_probes": [],
                "total_count": 0,
                "method_id": new_network_method.id
            }

            for i, h in enumerate(hits.split('\t')):
                try:
                    name, value = h.split('(')
                    value = float(value.replace(')', ''))
                    if value > pcc_cutoff:
                        network[query]["total_count"] += 1
                        if i < limit:
                            link = {"probe_name": name,
                                    "gene_name": name,
                                    "gene_id": sequence_dict[name.upper()] if name.upper() in sequence_dict.keys() else None,
                                    "link_score": i,
                                    "link_pcc": value}
                            network[query]["linked_probes"].append(link)
                            scores[query][name] = i
                except ValueError as e:
                    print("Error on line %d, skipping ... (%s)" % (i, str(h)), file=sys.stderr)

    # HRR
    hr_ranks = defaultdict(lambda: defaultdict(int))

    for query, targets in scores.items():
        for target, score in targets.items():
            if None in [score, scores[target][query]]:
                hr_ranks[query][target] = None
            else:
                # As scores start from 0 and ranks one, increase the hrr by one
                hr_ranks[query][target] = max(score, scores[target][query]) + 1

    # Dump dicts into network string, which will be loaded into the database
    for query in network.keys():

        for i, l in enumerate(network[query]["linked_probes"]):
            network[query]["linked_probes"][i]["hrr"] = hr_ranks[query][l["probe_name"]]

        # Dump links WITH HRR into json string
        network[query]["network"] = json.dumps([n for n in network[query]["linked_probes"] if n['hrr'] is not None])

    # add nodes in sets of 400 to avoid sending to much in a single query
    new_nodes = []
    for _, n in network.items():
        new_nodes.append(n)
        session.add(ExpressionNetwork(n))
        if len(new_nodes) > 400:
            session.commit()
            new_nodes = []

    session.commit()

    return new_network_method.id


db_admin = args.db_admin
db_name = args.db_name

create_engine_string = "mysql+pymysql://"+db_admin+":"+db_password+"@localhost/"+db_name

engine = create_engine(create_engine_string, echo=True)

# Reflect an existing database into a new model
Base = automap_base()

Base.prepare(engine, reflect=True)

Species = Base.classes.species
Sequence = Base.classes.sequences
ExpressionNetworkMethod = Base.classes.expression_network_methods
ExpressionNetwork = Base.classes.expression_networks

# Create a Session
Session = sessionmaker(bind=engine)
session = Session()

network_file = args.network_file
species_code = args.species_code
description = args.description

read_expression_network_lstrap(network_file, species_code, description, engine)

session.close()