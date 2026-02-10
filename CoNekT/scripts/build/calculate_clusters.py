#!/usr/bin/env python3

import argparse
import json
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select
from sqlalchemy.pool import NullPool

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from add.log_functions import *

parser = argparse.ArgumentParser(description='Clusterize network and add to CoNekT')
parser.add_argument('--network_method_id', type=int, metavar='1',
                    dest='network_method_id',
                    help='The network method ID',
                    required=True)
parser.add_argument('--description', type=str, metavar='Description',
                    dest='clustering_method_description',
                    help='Description of the clustering as it should appear in CoNekT Grasses',
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

args = parser.parse_args()

db_password = args.db_password if args.db_password else input("Enter the database password: ")


class HCCA:
    """
    HCCA class to create clusters from a Rank Based Network
    """

    def __init__(self, step_size=3, hrr_cutoff=50, min_cluster_size=40, max_cluster_size=200):
        self.hrrCutoff = hrr_cutoff
        self.stepSize = step_size
        self.min_cluster_size = min_cluster_size
        self.max_cluster_size = max_cluster_size
        self.scoreDic = {}
        self.curDic = {}
        self.loners = []
        self.clustered = []
        self.clustets = []

    def __clustettes(self, nodes):
        cons = []
        for l in nodes:
            cons += self.curDic[l]
        cons = list(set(cons + nodes))
        if len(cons) <= self.max_cluster_size:
            if len(cons) == len(nodes):
                cons.sort()
                if cons not in self.clustets:
                    self.clustets.append(cons)
            else:
                self.__clustettes(cons)

    def __remove_loners(self):
        logger.info("Detecting loners...")
        node_count = len(self.curDic)
        for node in self.curDic.keys():
            self.__clustettes([node])
        deleted_count = 0
        for clustet in self.clustets:
            for c in clustet:
                del self.curDic[c]
                deleted_count += 1
        logger.info(f"Found {deleted_count} loners (out of {node_count} nodes)")

    def __surrounding_step(self, node_list, whole, step):
        if step < self.stepSize:
            nvn = [l for l in node_list]
            for l in node_list:
                nvn += self.curDic[l]
            nvn = list(set(nvn))
            self.__surrounding_step(nvn, whole, step + 1)
        else:
            whole.append(node_list)

    def __chisel(self, nvn, clusters):
        temp = []
        seta = set(nvn)
        for n in nvn:
            connections = self.curDic[n]
            inside = set(nvn) & set(connections)
            outside = set(connections) - set(inside)
            in_score = sum(self.scoreDic[n][j] for j in inside)
            out_score = sum(self.scoreDic[n][j] for j in outside)
            if in_score > out_score:
                temp.append(n)
        if len(temp) == len(seta):
            clusters.append(temp)
        else:
            self.__chisel(temp, clusters)

    def __biggest_isle(self, lista, cluster_set, cur_seed):
        temp = []
        for k in range(len(lista)):
            temp += self.scoreDic[lista[k]].keys()
        nodes = set(temp + lista) & cluster_set
        if len(set(nodes)) == len(set(lista)):
            cur_seed.append(list(set(nodes)))
        else:
            self.__biggest_isle(list(nodes), cluster_set, cur_seed)

    def __find_non_overlapping(self, clusters):
        ranked_clust = []
        for cluster in clusters:
            in_score = out_score = 0
            for node in cluster:
                connections = set(self.scoreDic[node].keys())
                in_cons = list(connections & set(cluster))
                out_cons = list(connections - set(cluster))
                in_score += sum(self.scoreDic[node][in_con] for in_con in in_cons)
                out_score += sum(self.scoreDic[node][out_con] for out_con in out_cons)
            ranked_clust.append([out_score / in_score if in_score != 0 else float('inf'), cluster])
        ranked_clust.sort()
        best_clust = [ranked_clust[0][1]]
        for i in range(len(ranked_clust)):
            counter = 0
            for j in range(len(best_clust)):
                if len(set(ranked_clust[i][1]) & set(best_clust[j])) > 0:
                    counter += 1
                    break
            if counter == 0 and ranked_clust[i][0] < 1:
                best_clust.append(ranked_clust[i][1])
        return best_clust

    def __network_editor(self, clustered):
        connected = []
        clustered_nodes = []
        for cl in clustered:
            clustered_nodes += cl
            for node in cl:
                connected += self.curDic[node]
                del self.curDic[node]
        connections = list(set(connected) - set(clustered_nodes))
        for node in connections:
            self.curDic[node] = list(set(self.curDic[node]) - set(clustered_nodes))

    def __filler(self, left_overs):
        con_score_mat = [0] * len(self.clustered)
        clustera = []
        if len(left_overs) != 0:
            for i, node in enumerate(left_overs):
                for j, cluster in enumerate(self.clustered):
                    connections = list(set(self.scoreDic[node].keys()) & set(cluster))
                    con_score_mat[j] = sum(self.scoreDic[node][c] for c in connections)
                top_score = max(con_score_mat)
                if top_score != 0:
                    size_list = [[len(self.clustered[j]), j] for j, score in enumerate(con_score_mat) if score == top_score]
                    size_list.sort()
                    self.clustered[size_list[0][1]] += [node]
                    clustera.append(node)
            left_overs = list(set(left_overs) - set(clustera))
            self.__filler(left_overs)

    def __iterate(self):
        save = []
        not_clustered = list(self.curDic.keys())
        for i, node in enumerate(not_clustered):
            sys.stdout.write(f"\rNode {i} out of {len(not_clustered)}")
            sys.stdout.flush()
            whole = []
            clusters = []
            self.__surrounding_step([node], whole, 0)
            self.__chisel(whole[0], clusters)
            if len(clusters[0]) > 20:
                checked = []
                for j in range(len(clusters[0])):
                    if clusters[0][j] not in checked:
                        cur_seed = []
                        self.__biggest_isle([clusters[0][j]], set(clusters[0]), cur_seed)
                        checked += cur_seed[0]
                        if self.max_cluster_size > len(cur_seed[0]) > self.min_cluster_size:
                            save.append(cur_seed[0])
                            break
        new_cluster = self.__find_non_overlapping(save)
        self.clustered += new_cluster
        self.__network_editor(new_cluster)

    def build_clusters(self):
        self.__remove_loners()
        iteration = 1
        while True:
            try:
                logger.info(f"Iteration {iteration}...")
                self.__iterate()
                iteration += 1
            except IndexError:
                leftovers = list(self.curDic.keys())
                self.__filler(leftovers)
                break

    def load_data(self, data):
        logger.info("Loading network from dictionary...")
        self.curDic = {}
        self.scoreDic = {}
        self.loners = []
        for gene, scores in data.items():
            neighbors = [k for k, score in scores.items() if score < self.hrrCutoff]
            if len(neighbors) == 0:
                self.loners.append(gene)
            else:
                self.curDic[gene] = neighbors
        for gene, scores in data.items():
            self.scoreDic[gene] = {k: 1/(score + 1) for k, score in scores.items() if score < self.hrrCutoff}

    @property
    def clusters(self):
        output = []
        count = 1
        for cluster in self.clustered:
            for member in cluster:
                output.append((member, f"Cluster_{count}", False))
            count += 1
        for clustet in self.clustets:
            for member in clustet:
                output.append((member, f"Cluster_{count}", True))
            count += 1
        return output



def build_hcca_clusters(clustering_method, network_method_id, step_size=3, hrr_cutoff=30,
                        min_cluster_size=40, max_cluster_size=200):
    network_data = {}
    sequence_probe = {}

    logger.info(f"🔍 Retrieving network method ID {network_method_id} for clustering '{clustering_method}'...")

    # Retrieve ExpressionNetworkMethod
    with engine.connect() as conn:
        stmt = select([ExpressionNetworkMethod]).where(
            ExpressionNetworkMethod.__table__.c.id == network_method_id
        )
        method = conn.execute(stmt).fetchone()

    if not method:
        logger.error("❌ Network method not found!")
        exit(1)
    else:
        logger.debug(f"✅ Network method retrieved: {method.method if hasattr(method, 'method') else 'N/A'}")

    # Retrieve ExpressionNetwork records
    logger.info("📥 Loading expression network records from DB...")
    with engine.connect() as conn:
        stmt = select([ExpressionNetwork]).where(
            ExpressionNetwork.__table__.c.method_id == network_method_id
        )
        probes = conn.execute(stmt).fetchall()
        logger.info(f"✅ Retrieved {len(probes)} probes from ExpressionNetwork")

    # Build adjacency data
    logger.info("🧩 Building adjacency data from probes...")
    for p in probes:
        if p.sequence_id is not None:
            neighborhood = json.loads(p.network)
            network_data[p.sequence_id] = {
                nb["gene_id"]: nb["hrr"]
                for nb in neighborhood
                if "gene_id" in nb and "hrr" in nb and nb["gene_id"] is not None
            }
            sequence_probe[p.sequence_id] = p.probe
    logger.debug(f"📊 Adjacency data prepared for {len(network_data)} sequences")

    # Ensure reciprocity
    logger.info("🔄 Ensuring network reciprocity...")
    for seq, data in network_data.items():
        for neighbor, score in data.items():
            if neighbor not in network_data:
                network_data[neighbor] = {seq: score}
            elif seq not in network_data[neighbor]:
                network_data[neighbor][seq] = score
    logger.debug("✅ Reciprocity ensured")

    # Run HCCA
    logger.info("🏗 Running HCCA clustering...")
    hcca_util = HCCA(step_size=step_size, hrr_cutoff=hrr_cutoff,
                     min_cluster_size=min_cluster_size, max_cluster_size=max_cluster_size)
    hcca_util.load_data(network_data)
    hcca_util.build_clusters()
    logger.info(f"✅ HCCA completed, {len(hcca_util.clusters)} cluster assignments generated")

    clusters = list(set([t[1] for t in hcca_util.clusters]))
    if clusters:
        logger.info(f"📌 Adding {len(clusters)} unique clusters to the database")

        new_method = CoexpressionClusteringMethod()
        new_method.network_method_id = network_method_id
        new_method.method = clustering_method
        new_method.cluster_count = len(clusters)
        session.add(new_method)
        session.commit()
        logger.debug(f"✅ Clustering method '{clustering_method}' added with ID {new_method.id}")

        # Create cluster objects
        cluster_dict = {}
        for c in clusters:
            cluster_obj = CoexpressionCluster()
            cluster_obj.method_id = new_method.id
            cluster_obj.name = c
            session.add(cluster_obj)
            session.commit()
            cluster_dict[c] = cluster_obj
        logger.debug(f"✅ {len(cluster_dict)} CoexpressionCluster objects created")

        # Add associations in batches
        logger.info("🔗 Adding sequence-cluster associations...")
        for i, t in enumerate(hcca_util.clusters):
            gene_id, cluster_name, _ = t
            cluster_obj = cluster_dict.get(cluster_name)
            if not cluster_obj:
                logger.warning(f"⚠️ Cluster '{cluster_name}' not found for gene ID {gene_id}")
                continue

            relation = SequenceCoexpressionClusterAssociation()
            relation.probe = sequence_probe.get(gene_id)
            relation.sequence_id = gene_id
            relation.coexpression_cluster_id = cluster_obj.id
            session.add(relation)

            if i > 0 and i % 400 == 0:
                logger.debug(f"📦 Committing batch of {i} associations...")
                session.commit()

        session.commit()
        logger.info(f"✅ All {len(hcca_util.clusters)} sequence-cluster associations committed")
    else:
        logger.warning("⚠️ No clusters found! Nothing added to DB")




try:
    thisFileName = os.path.basename(__file__)
    log_dir = args.log_dir
    log_file_name = "calculate_clusters"
    db_verbose = str2bool(args.db_verbose)
    py_verbose = str2bool(args.py_verbose)
    logger = setup_logger(log_dir=log_dir, base_filename=log_file_name, DBverbose=db_verbose, PYverbose=py_verbose)

    create_engine_string = f"mysql+pymysql://{args.db_admin}:{db_password}@localhost/{args.db_name}"
    engine = create_engine(create_engine_string, echo=db_verbose, poolclass=NullPool)

    Base = automap_base()
    Base.prepare(engine, reflect=True)

    CoexpressionClusteringMethod = Base.classes.coexpression_clustering_methods
    CoexpressionCluster = Base.classes.coexpression_clusters
    ExpressionNetworkMethod = Base.classes.expression_network_methods
    ExpressionNetwork = Base.classes.expression_networks
    SequenceCoexpressionClusterAssociation = Base.classes.sequence_coexpression_cluster

    Session = sessionmaker(bind=engine)
    session = Session()

    build_hcca_clusters(args.clustering_method_description, args.network_method_id)

    session.close()

except Exception as e:
    print_log_error(logger, e)
    logger.info(f" ---- ❌ An error occurred while executing {thisFileName}. Please fix the issue and rerun the script. ❌ ---- ")
    exit(1)

logger.info(f" ---- ✅ SUCCESS: All operations from {thisFileName} finished without errors! ✅ ---- ")
