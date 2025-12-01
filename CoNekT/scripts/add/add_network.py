#!/usr/bin/env python3
import getpass
import argparse
import psutil
import json
import sys

from collections import defaultdict

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select
from sqlalchemy.pool import NullPool

from log_functions import *

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
parser.add_argument('--hrr_score_threshold', type=int, metavar='hrr score threshold',
                    dest='hrr_score_threshold',
                    help='hrr score threshold, pairs with a score above this will be ignored',
                    required=False)
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
parser.add_argument('--db_password', type=str, metavar='DB password',
                    dest='db_password',
                    help='The database password',
                    required=False)
parser.add_argument('--logdir', type=str, metavar='Log diretory',
                    dest='log_dir',
                    help='The directory containing temporary populate logs',
                    required=False)
parser.add_argument('--db_verbose', type=str, metavar='Database verbose',
                    dest='db_verbose',
                    help='Enable database verbose logging (true/false)',
                    required=False,
                    default="false")
parser.add_argument('--py_verbose', type=str, metavar='Python script verbose',
                    dest='py_verbose',
                    help='Enable python verbose logging (true/false)',
                    required=False,
                    default="true")
parser.add_argument('--first_run', type=str, metavar='Flag indicating first execution of the file',
                    dest='first_run',
                    help='Controls log file opening type',
                    required=False,
                    default="true")

args = parser.parse_args()

if args.db_password:
    db_password = args.db_password
else:
    db_password = getpass.getpass("Enter the database password: ")

# def print_memory_usage():
#     # Get memory usage statistics
#     memory = psutil.virtual_memory()

#     # Print memory usage
#     print(f"Total Memory: {memory.total / (1024.0 ** 3):.2f} GB")
#     print(f"Available Memory: {memory.available / (1024.0 ** 3):.2f} GB")
#     print(f"Used Memory: {memory.used / (1024.0 ** 3):.2f} GB")
#     print(f"Memory Usage Percentage: {memory.percent}%\n")



def read_expression_network_lstrap(network_file, species_code, description, engine,
                                   score_type="rank", pcc_cutoff=0.7, limit=100,
                                   enable_second_level=False):
    """
    Reads a network from disk (LSTrAP output), computes HRR scores for each gene pair,
    and stores the network in the database.

    :param network_file: path to input file
    :param species_code: species code
    :param description: description of the network method
    :param score_type: score type to use ("rank" by default)
    :param pcc_cutoff: minimum PCC threshold
    :param limit: maximum number of top hits (HRR threshold)
    :param enable_second_level: include second level neighborhood
    :return: internal ID of the new network method
    """
    logger.info("______________________________________________________________________")
    logger.info(f"➡️  Adding network for '{species_code}':")

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        logger.debug(f"Searching for species '{species_code}' in database")
        species = session.query(Species).filter(Species.code == species_code).first()
        if not species:
            print_log_error(logger, f"Species '{species_code}' not found in database")
            session.close()
            exit(1)
        species_id = species.id
        logger.debug(f"✅ Species found (ID: {species_id})")
    except Exception as e:
        print_log_error(logger, f"Error while querying species '{species_code}': {e}")
        session.close()
        exit(1)

    try:
        logger.debug(f"Retrieving protein-coding sequences for species '{species_code}'")
        sequences = session.query(Sequence).filter(
            Sequence.species_id == species_id,
            Sequence.type == 'protein_coding'
        ).all()
        sequence_dict = {s.name.upper(): s.id for s in sequences}
        logger.debug(f"Retrieved {len(sequences)} sequences")
    except Exception as e:
        print_log_error(logger, f"Error while retrieving sequences: {e}")
        session.close()
        exit(1)

    # Add network method
    try:
        network_method = session.query(ExpressionNetworkMethod).filter(
            ExpressionNetworkMethod.description == description
        ).first()

        if network_method:
            print_log_error(logger, f"Network method already exists: {description}")
            session.close()
            exit(1)

        new_network_method = ExpressionNetworkMethod(
            species_id=species_id,
            description=description,
            edge_type=score_type,
            hrr_cutoff=limit,
            pcc_cutoff=pcc_cutoff,
            enable_second_level=enable_second_level
        )
        session.add(new_network_method)
        session.commit()
        logger.info(f"✅ New network method created (ID: {new_network_method.id})")
    except Exception as e:
        print_log_error(logger, f"Error while adding network method: {e}")
        session.rollback()
        session.close()
        exit(1)

    network = {}
    scores = defaultdict(lambda: defaultdict(lambda: None))  # Score for non-existing pairs will be None

    # Read network file
    try:
        with open(network_file) as fin:
            for linenr, line in enumerate(fin):
                try:
                    query, hits = line.strip().split(' ')
                    query = query.replace(':', '')
                except ValueError:
                    logger.warning(f"⚠️ Error parsing line {linenr}: '{line.strip()}'. Skipping.")
                    continue

                network[query] = {
                    "probe": query,
                    "sequence_id": sequence_dict.get(query.upper()),
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
                                link = {
                                    "probe_name": name,
                                    "gene_name": name,
                                    "gene_id": sequence_dict.get(name.upper()),
                                    "link_score": i,
                                    "link_pcc": value
                                }
                                network[query]["linked_probes"].append(link)
                                scores[query][name] = i
                    except ValueError:
                        logger.warning(f"⚠️ Error parsing hit '{h}' for query '{query}' (line {linenr})")
    except Exception as e:
        print_log_error(logger, f"Error while reading network file '{network_file}': {e}")
        session.close()
        exit(1)

    # Compute HRR
    hr_ranks = defaultdict(lambda: defaultdict(int))
    for query, targets in scores.items():
        for target, score in targets.items():
            if None in [score, scores[target].get(query)]:
                hr_ranks[query][target] = None
            else:
                hr_ranks[query][target] = max(score, scores[target][query]) + 1

    # Update network dict with HRR
    for query in network.keys():
        for i, l in enumerate(network[query]["linked_probes"]):
            l["hrr"] = hr_ranks[query][l["probe_name"]]
        network[query]["network"] = json.dumps(
            [n for n in network[query]["linked_probes"] if n['hrr'] is not None]
        )

    # Add nodes to DB in batches
    try:
        batch = []
        for n in network.values():
            batch.append(n)
            session.add(ExpressionNetwork(
                network=n["network"],
                probe=n["probe"],
                sequence_id=n["sequence_id"],
                method_id=n["method_id"]
            ))
            if len(batch) >= 400:
                session.commit()
                batch = []
        if batch:
            session.commit()
        logger.info(f"✅ Network nodes added to database for '{description}'")
    except Exception as e:
        print_log_error(logger, f"Error while inserting network nodes: {e}")
        session.rollback()
        session.close()
        exit(1)

    method_id = new_network_method.id
    session.close()
    return method_id




try:
    thisFileName = os.path.basename(__file__)

    # Log variables
    log_dir = args.log_dir
    log_file_name = "add_network"  # e.g. "gene_ontologies"
    db_verbose = str2bool(args.db_verbose)
    py_verbose = str2bool(args.py_verbose)
    first_run = str2bool(args.first_run)

    logger = setup_logger(log_dir=log_dir,
                          base_filename=log_file_name,
                          DBverbose=db_verbose,
                          PYverbose=py_verbose,
                          overwrite_logs=first_run)

    db_admin = args.db_admin
    db_name = args.db_name

    create_engine_string = "mysql+pymysql://"+db_admin+":"+db_password+"@localhost/"+db_name

    engine = create_engine(create_engine_string, echo=db_verbose, poolclass=NullPool)

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

    if args.hrr_score_threshold:
        read_expression_network_lstrap(network_file, species_code, description, engine, limit=args.hrr_score_threshold)
    else:
        read_expression_network_lstrap(network_file, species_code, description, engine)

    session.close()

except Exception as e:
    print_log_error(logger, e)
    logger.info(f" ---- ❌ An error occurred while executing {thisFileName}. Please fix the issue and rerun the script. ❌ ---- ")
    exit(1)

logger.info(f" ---- ✅ SUCCESS: All operations from {thisFileName} for '{species_code}' finished without errors! ✅ ---- ")