#!/usr/bin/env python3

import getpass
import argparse
import os
import sys
import logging
import json

# Add CoNekT path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import delete

from log_functions import *
from utils.parser.sequence_ontology import SequenceOntologyParser

# Create arguments
parser = argparse.ArgumentParser(description='Add sequence ontology data to the database')
parser.add_argument('--sequence_ontology', type=str, metavar='seq_ontology.txt',
					dest='so_file',
					help='The sequence ontology file',
					required=False)
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
					help='Enable databaseverbose logging (true/false)',
					required=False,
					default="false")
parser.add_argument('--py_verbose', type=str, metavar='Python script verbose',
					dest='py_verbose',
					help='Enable python verbose logging (true/false)',
					required=False,
					default="true")

args = parser.parse_args()

if args.db_password:
	db_password = args.db_password
else:
	db_password = getpass.getpass("Enter the database password: ")

def add_sequence_ontology(filename, empty=True):
	"""
	Add the Sequence Ontology from a custom format file to the database.
	If empty is True, it will first empty the table.
	"""
	
	logger.info("______________________________________________________________________")
	logger.info("➡️  Adding Sequence Ontology data:")

	# If required empty the table first
	file_size = os.stat(filename).st_size
	if empty and file_size > 0:
		try:
			logger.debug("Cleaning 'sequence_ontologies' table...")
			with engine.connect() as conn:
				stmt = delete(SequenceOntology)
				conn.execute(stmt)
			logger.debug("✅  Table cleaned successfully.")
		except Exception as e:
			print_log_error(logger, f"Error while cleaning 'sequence_ontologies' table: {e}")
			exit(1)

	parser_so = SequenceOntologyParser()
	parser_so.parse_custom_format(filename)
	so_entries = parser_so.export_to_dict()
	logger.debug(f"Reading Sequence Ontology file: {filename}")

	for i, entry in enumerate(so_entries):
		# Check if this SO term already exists
		existing_so = session.query(SequenceOntology).filter_by(so_id=entry['so_term']).first()
		if existing_so:
			logger.debug(f"SO term {entry['so_term']} already exists, skipping...")
			continue
			
		so = SequenceOntology(
			so_id=entry['so_term'],
			name=entry['so_name'],
			description=entry.get('so_description'),
			namespace=entry.get('so_namespace'),
			alias=entry.get('aliases', '')
		)
		session.add(so)
		
		if i % 500 == 0:
			# commit to the db frequently to allow WHOOSHEE's indexing function to work without timing out
			try:
				session.commit()
				logger.debug(f"{i} entries processed and committed...")
			except Exception as e:
				session.rollback()
				print_log_error(logger, f"Failed while inserting Sequence Ontology entry number {i + 1}: {e}")
				exit(1)

	try:
		session.commit()
		logger.info(f"✅  All {len(so_entries)} entries added to table 'sequence_ontologies' successfully!")
	except Exception as e:
		session.rollback()
		print_log_error(logger, f"Failed while inserting Sequence Ontology entry number {i + 1}: {e}")
		exit(1)

	# Create associations with TE classes
	logger.info("______________________________________________________________________")
	logger.info("➡️  Adding SO-TE Class associations:")

	# Get all TE classes with their aliases
	te_classes = session.query(TEClass).all()
	te_class_dict = {}
	te_alias_dict = {}
	
	# Build dictionaries for direct matching
	for tc in te_classes:
		# Index by TE class name
		te_class_dict[tc.name] = tc
		
		# Index by TE class aliases if they exist
		if hasattr(tc, 'aliases') and tc.aliases:
			aliases = [a.strip() for a in tc.aliases.split(',') if a.strip()]
			for alias in aliases:
				te_alias_dict[alias] = tc
	
	associations_created = 0
	
	for entry in so_entries:
		so_term = session.query(SequenceOntology).filter_by(so_id=entry['so_term']).first()
		if not so_term:
			continue
			
		so_name = entry['so_name']
		aliases_str = entry.get('aliases', '')
		so_aliases = []
		if aliases_str:
			so_aliases = [a.strip() for a in aliases_str.split(',') if a.strip()]
		
		# Direct matches: SO name with TE class name
		if so_name in te_class_dict:
			te_class = te_class_dict[so_name]
			existing = session.query(TEClassSOAssociation).filter_by(
				te_class_id=te_class.id,
				sequence_ontology_id=so_term.id
			).first()
			
			if not existing:
				new_assoc = TEClassSOAssociation(
					te_class_id=te_class.id,
					sequence_ontology_id=so_term.id,
					evidence_code='IEA',
					confidence=1.0,
					source='seq_ontology_import'
				)
				session.add(new_assoc)
				associations_created += 1
		
		# Direct matches: SO name with TE class alias
		if so_name in te_alias_dict:
			te_class = te_alias_dict[so_name]
			existing = session.query(TEClassSOAssociation).filter_by(
				te_class_id=te_class.id,
				sequence_ontology_id=so_term.id
			).first()
			
			if not existing:
				new_assoc = TEClassSOAssociation(
					te_class_id=te_class.id,
					sequence_ontology_id=so_term.id,
					evidence_code='IEA',
					confidence=1.0,
					source='seq_ontology_import'
				)
				session.add(new_assoc)
				associations_created += 1
		
		# Direct matches: SO aliases with TE class name or alias
		for so_alias in so_aliases:
			# SO alias with TE class name
			if so_alias in te_class_dict:
				te_class = te_class_dict[so_alias]
				existing = session.query(TEClassSOAssociation).filter_by(
					te_class_id=te_class.id,
					sequence_ontology_id=so_term.id
				).first()
				
				if not existing:
					new_assoc = TEClassSOAssociation(
						te_class_id=te_class.id,
						sequence_ontology_id=so_term.id,
						evidence_code='IEA',
						confidence=1.0,
						source='seq_ontology_import'
					)
					session.add(new_assoc)
					associations_created += 1
			
			# SO alias with TE class alias
			if so_alias in te_alias_dict:
				te_class = te_alias_dict[so_alias]
				existing = session.query(TEClassSOAssociation).filter_by(
					te_class_id=te_class.id,
					sequence_ontology_id=so_term.id
				).first()
				
				if not existing:
					new_assoc = TEClassSOAssociation(
						te_class_id=te_class.id,
						sequence_ontology_id=so_term.id,
						evidence_code='IEA',
						confidence=1.0,
						source='seq_ontology_import'
					)
					session.add(new_assoc)
					associations_created += 1
		
		if associations_created % 500 == 0:
			try:
				session.commit()
				logger.debug(f"{associations_created} associations processed and committed...")
			except Exception as e:
				session.rollback()
				print_log_error(logger, f"Failed while creating associations: {e}")
				exit(1)

	try:
		session.commit()
		logger.info(f"✅  All {associations_created} associations added successfully!")
	except Exception as e:
		session.rollback()
		print_log_error(logger, f"Failed while creating associations: {e}")
		exit(1)

try:

	thisFileName = os.path.basename(__file__)
	#log variables
	log_dir = args.log_dir  #log dir path
	log_file_name = "sequence_ontology"   #log file names
	db_verbose = str2bool(args.db_verbose)
	py_verbose = str2bool(args.py_verbose)
	logger = setup_logger(log_dir=log_dir, base_filename=log_file_name, DBverbose=db_verbose, PYverbose=py_verbose)

	db_admin = args.db_admin
	db_name = args.db_name

	create_engine_string = "mysql+pymysql://"+db_admin+":"+db_password+"@localhost/"+db_name

	engine = create_engine(create_engine_string, echo=db_verbose)

	# Reflect an existing database into a new model
	Base = automap_base()

	Base.prepare(engine, reflect=True)

	SequenceOntology = Base.classes.sequence_ontologies
	TEClass = Base.classes.te_classes
	TEClassSOAssociation = Base.classes.te_class_so

	# Create a Session
	Session = sessionmaker(bind=engine)
	session = Session()

	so_file = args.so_file

	ontology_data_count = 0

	if so_file:
		ontology_data_count+=1
		add_sequence_ontology(so_file)

	if ontology_data_count == 0:
		print_log_error(logger, "Must add at least one type of ontology file (e.g., --sequence_ontology)")
		exit(1)

	session.close()

except Exception as e:
	print_log_error(logger, e)
	logger.info(f" ---- ❌ An error occurred while executing {thisFileName}. Please fix the issue and rerun the script. ❌ ---- ")
	exit(1)

logger.info(f" ---- ✅ SUCCESS: All operations from {thisFileName} finished without errors! ✅ ---- ")