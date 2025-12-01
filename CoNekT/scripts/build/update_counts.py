#!/usr/bin/env python3

import argparse
import os
import sys

from sqlalchemy import create_engine, func, update
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from add.log_functions import *  # logging utilities

# Create arguments
parser = argparse.ArgumentParser(description='Update all counts in the CoNekT Grasses database')
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
parser.add_argument('--logdir', type=str, metavar='Log directory',
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
db_password = args.db_password or input("Enter the database password: ")

try:
	thisFileName = os.path.basename(__file__)
	log_dir = args.log_dir
	log_file_name = "update_counts"
	db_verbose = str2bool(args.db_verbose)
	py_verbose = str2bool(args.py_verbose)

	logger = setup_logger(log_dir=log_dir,
						  base_filename=log_file_name,
						  DBverbose=db_verbose,
						  PYverbose=py_verbose,
						  overwrite_logs=True)

	engine_string = f"mysql+pymysql://{args.db_admin}:{db_password}@localhost/{args.db_name}"
	engine = create_engine(engine_string, echo=db_verbose)

	# Reflect an existing database into a new model
	Base = automap_base()

	# Use the engine to reflect the database
	Base.prepare(engine, reflect=True)

	# Map tables
	Sequence = Base.classes.sequences
	CoexpressionClusteringMethod = Base.classes.coexpression_clustering_methods
	CoexpressionCluster = Base.classes.coexpression_clusters
	ExpressionNetwork = Base.classes.expression_networks
	ExpressionNetworkMethod = Base.classes.expression_network_methods
	ExpressionProfile = Base.classes.expression_profiles
	GeneFamily = Base.classes.gene_families
	GeneFamilyMethod = Base.classes.gene_family_methods
	TEClass = Base.classes.te_classes
	TEClassMethod = Base.classes.te_class_methods
	TEdistill = Base.classes.tedistills
	TEdistillMethod = Base.classes.tedistill_methods
	Species = Base.classes.species
	GO = Base.classes.go

	# Create a Session
	Session = sessionmaker(bind=engine)
	session = Session()

	# Update Functions
	def update_coexpression_cluster_count():
		try:
			logger.info("Updating coexpression cluster counts...")
			methods = session.query(CoexpressionClusteringMethod).all()
			for m in methods:
				count = session.query(func.count()).filter(CoexpressionCluster.method_id == m.id).scalar()
				session.execute(
					update(CoexpressionClusteringMethod)
					.where(CoexpressionClusteringMethod.id == m.id)
					.values(cluster_count=count)
				)
			session.commit()
			logger.info("Coexpression cluster counts updated successfully.")
		except Exception as e:
			session.rollback()
			print_log_error(logger, e)
			raise

	def update_network_count():
		try:
			logger.info("Updating network counts...")
			methods = session.query(ExpressionNetworkMethod).all()
			for m in methods:
				count = session.query(func.count()).filter(ExpressionNetwork.method_id == m.id).scalar()
				session.execute(
					update(ExpressionNetworkMethod)
					.where(ExpressionNetworkMethod.id == m.id)
					.values(probe_count=count)
				)
			session.commit()
			logger.info("Network counts updated successfully.")
		except Exception as e:
			session.rollback()
			print_log_error(logger, e)
			raise

	def update_gene_family_count():
		try:
			logger.info("Updating gene family counts...")
			methods = session.query(GeneFamilyMethod).all()
			for m in methods:
				count = session.query(func.count()).filter(GeneFamily.method_id == m.id).scalar()
				session.execute(
					update(GeneFamilyMethod)
					.where(GeneFamilyMethod.id == m.id)
					.values(family_count=count)
				)
			session.commit()
			logger.info("Gene family counts updated successfully.")
		except Exception as e:
			session.rollback()
			print_log_error(logger, e)
			raise

	def update_tedistill_count():
		try:
			logger.info("Updating TEdistill counts...")
			methods = session.query(TEdistillMethod).all()
			for m in methods:
				count = session.query(func.count()).filter(TEdistill.method_id == m.id).scalar()
				session.execute(
					update(TEdistillMethod)
					.where(TEdistillMethod.id == m.id)
					.values(tedistill_count=count)
				)
			session.commit()
			logger.info("TEdistill counts updated successfully.")
		except Exception as e:
			session.rollback()
			print_log_error(logger, e)
			raise

	def update_te_class_count():
		try:
			logger.info("Updating TEClass counts...")
			methods = session.query(TEClassMethod).all()
			for m in methods:
				count = session.query(func.count()).filter(TEClass.method_id == m.id).scalar()
				session.execute(
					update(TEClassMethod)
					.where(TEClassMethod.id == m.id)
					.values(te_class_count=count)
				)
			session.commit()
			logger.info("TEClass counts updated successfully.")
		except Exception as e:
			session.rollback()
			print_log_error(logger, e)
			raise

	def update_species_counts():
		try:
			logger.info("Updating species counts...")
			species_list = session.query(Species).all()
			for s in species_list:
				seq_count = session.query(func.count()).filter(
					Sequence.species_id == s.id,
					Sequence.type == 'protein_coding'
				).scalar()

				profile_count = session.query(func.count()).filter(
					ExpressionProfile.species_id == s.id
				).scalar()

				network_count = session.query(func.count()).filter(
					ExpressionNetworkMethod.species_id == s.id
				).scalar()

				session.execute(
					update(Species)
					.where(Species.id == s.id)
					.values(
						sequence_count=seq_count,
						profile_count=profile_count,
						network_count=network_count
					)
				)
			session.commit()
			logger.info("Species counts updated successfully.")
		except Exception as e:
			session.rollback()
			print_log_error(logger, e)
			raise

	"""
	Updates pre-computed counts in the database.

	"""
	logger.info("Starting all count updates...")
	update_coexpression_cluster_count()
	update_network_count()
	update_gene_family_count()
	update_species_counts()
	update_tedistill_count()
	update_te_class_count()
	#TODO: implement GO.update_species_counts()
	logger.info("All count updates completed successfully.")

	session.close()

except Exception as e:
	print_log_error(logger, e)
	logger.info(f" ---- ❌ An error occurred while executing {thisFileName}. Please fix the issue and rerun the script. ❌ ---- ")
	exit(1)

logger.info(f" ---- ✅ SUCCESS: All operations from {thisFileName} finished without errors! ✅ ---- ")
