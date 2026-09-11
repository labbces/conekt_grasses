#!/usr/bin/env python3

import getpass
import argparse
import os
import operator
import re
import time
import math

import sys
import logging

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select

from crossref.restful import Works
from log_functions import *

from utils.fasta import Fasta

parser = argparse.ArgumentParser(description='Add species to the database')
parser.add_argument('--input_table', type=str, metavar='conekt_species.tsv',
					dest='species_file',
					help='The TSV file with the species information',
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
parser.add_argument('--species_dir', type=str, metavar='Species data diretory',
					dest='species_dir',
					help='The directory containing species data',
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

def add_literature(doi, session):
		
	# logger.info("______________________________________________________________________")
	logger.info(f"➡️  Adding literature entry: {doi}")

	try:

		works = Works()
		# verify if DOI already exists in DB, if not, collect data
		literature_info = works.doi(doi)

		qtd_author = len(literature_info['author'])
		
		if 'family' in literature_info['author'][0].keys():
			author_names = literature_info['author'][0]['family']
		else:
			author_names = literature_info['author'][0]['name']

		title = literature_info['title']
		
		if 'published-print' in literature_info.keys():
			public_year = literature_info['published-print']['date-parts'][0][0]
		elif 'published-online' in literature_info.keys():
			public_year = literature_info['published-online']['date-parts'][0][0]
		else:
			public_year = literature_info['issued']['date-parts'][0][0]
	
	except Exception as e:
		print_log_error(logger, f"Error while retrieving metadata for DOI '{doi}': {e}")
		exit(1)

	try:
		new_literature = LiteratureItem(qtd_author=qtd_author,
										author_names=author_names,
										title=title,
										public_year=public_year,
										doi=doi)
	except Exception as e:
		print_log_error(logger, f"Error while querying literature table for DOI '{doi}': {e}")
		exit(1)
	
	try:
		# stmt = select(LiteratureItem).where(LiteratureItem.doi == doi)
		literature = session.query(LiteratureItem).filter(LiteratureItem.doi == doi).first()
	except Exception as e:
		print_log_error(logger, f" Error while querying literature table for DOI '{doi}': {e}")
		exit(1)

	try:
		# literature is not in the DB yet, add it
		if not literature:
			session.add(new_literature)
			session.commit()
			logger.debug(f"✅  New literature entry added for DOI: {doi}")
			return new_literature.id
		else:
			logger.debug(f"✅  Literature with DOI '{doi}' already exists. Skipping insertion.")
			return literature.id
	except Exception as e:
		session.rollback()
		print_log_error(logger, f"Error while inserting literature entry for DOI '{doi}': {e}")
		exit(1)


def add_species(code, name, session, data_type='genome',
			color="#C7C7C7", highlight="#DEDEDE", description=None,
			source=None, literature_id=None, genome_version=None):
		
	logger.info("______________________________________________________________________")
	logger.info(f"➡️  Adding species '{name}' (code: {code}) infos:")

	try:
		new_species = Species(code=code,
							  name=name,
							  data_type=data_type,
							  color=color,
							  highlight=highlight,
							  description=description,
							  source=source,
							  non_coding_seq_count = 0,
							  te_count = 0,
							  profile_count = 0,
							  network_count = 0,
							  literature_id=literature_id,
							  genome_version=genome_version)
	except Exception as e:
		print_log_error(logger, f"Error while creating Species object for code '{code}': {e}")
		exit(1)

	try:
		with engine.connect() as conn:
			species = session.query(Species).filter(Species.code == code).first()
	except Exception as e:
		print_log_error(logger, f"Error while querying existing species with code '{code}': {e}")
		exit(1)

	try:
		# species is not in the DB yet, add it
		if not species:
			session.add(new_species)
			session.commit()
			logger.debug(f"✅  New species '{name}' (code: {code}) added successfully.")
			return new_species.id
		else:
			logger.debug(f"ℹ✅  Species with code '{code}' already exists. Skipping insertion.")
			return species.id
		
	except Exception as e:
		session.rollback()
		print_log_error(logger, f"Failed while inserting species '{name}' (code: {code}): {e}")
		exit(1)

def get_te_class(te_class_name):

	with engine.connect() as conn:
		stmt = select(TEClass.__table__.c).where(TEClass.name == te_class_name)
		te_class = conn.execute(stmt).first()

	if te_class:
		return te_class.id
	else:
		return None

def load_te_class_mapping(filtered_out_file):
	"""
	Parses a RepeatMasker .filtered.out file and returns a dict mapping
	repeat/family name to its class/family string.

	:param filtered_out_file: path to the .filtered.out file
	:return: dict {repeat_name: class_family_string}
	"""
	mapping = {}
	with open(filtered_out_file, 'r') as f:
		for line in f:
			line = line.strip()
			# Skip header lines and empty lines
			if not line or line.startswith('SW') or line.startswith('score'):
				continue
			parts = line.split()
			# RepeatMasker .out format:
			# SW_score div del ins query begin end (left) strand repeat class/family ...
			if len(parts) < 11:
				continue
			repeat_name = parts[9]
			te_class = parts[10]
			mapping[repeat_name] = te_class
	logger.debug(f"✅  Loaded {len(mapping)} unique family→class mappings from {filtered_out_file}")
	return mapping


def add_from_fasta(species_code, species_id, compressed=False, sequence_type='protein_coding'):
	logger.info("______________________________________________________________________")
	logger.info(f"➡️  Adding {sequence_type} sequences")

	ftype_map = {
		'protein_coding': 'cds',
		'RNA': 'rnas',
	}

	# TE sequences: use {code}_te_copies.fa + {code}_te_copies.fa.filtered.out (RepeatMasker format)
	te_class_mapping = {}
	use_filtered_out = False

	if sequence_type == 'TE':
		filename = f"{args.species_dir}/{species_code}/{species_code}_te_copies.fa"
		if not os.path.exists(filename):
			logger.warning(f"⚠️  No TE copies file found for {species_code} at '{filename}'. Skipping TE loading.")
			return 0
		filtered_out_file = filename + ".filtered.out"
		if not os.path.exists(filtered_out_file):
			logger.warning(f"⚠️  No .filtered.out found for '{filename}'. Skipping TE loading for {species_code}.")
			return 0
		logger.info(f"📂 Using real TE data: {filename}")
		logger.info(f"📂 Loading class mapping from: {filtered_out_file}")
		te_class_mapping = load_te_class_mapping(filtered_out_file)
		use_filtered_out = True
	else:
		ftype = ftype_map.get(sequence_type)
		if not ftype:
			raise ValueError(f"Unsupported sequence type: {sequence_type}")
		filename = f"{args.species_dir}/{species_code}/{species_code}_{ftype}.fa"

	try:
		logger.debug(f"Reading FASTA file: {filename}")
		fasta_data = Fasta()
		fasta_data.readfile(filename, compressed=compressed)
	except Exception as e:
		print_log_error(logger, f"Error while reading FASTA file '{filename}': {e}")
		#exit(1)

	total_sequences = len(fasta_data.sequences)
	logger.debug(f"Found {total_sequences} sequences in the FASTA file.")

	new_sequences = []
	counter = 0

	try:
		# Loop over sequences, sorted by name (key here) and add to db
		for line, sequence in sorted(fasta_data.sequences.items(), key=operator.itemgetter(0)):

			if sequence_type == 'TE' and use_filtered_out:
				# Real format: "TE_00006446_copy0001|chrom:start-end|strand family=TE_00006446 ..."
				name = line.split('|')[0]
				family_match = re.search(r'family=(\S+)', line)
				if family_match:
					family_name = family_match.group(1)
				else:
					family_name = re.sub(r'_copy\d+$', '', name)
				te_class_name = te_class_mapping.get(family_name, 'Unknown')
			else:
				# Legacy format: "name#te_class"
				name = line.split('#')[0]
				te_class_name = line.split('#')[1] if sequence_type == 'TE' else None

			new_sequence = {"species_id": species_id,
							"name": name,
							"description": None,
							"coding_sequence": sequence,
							"type": sequence_type,
							"is_mitochondrial": False,
							"is_chloroplast": False}

			new_sequence_obj = Sequence(**new_sequence)
			session.add(new_sequence_obj)
			counter+=1

			if sequence_type == 'TE':
				session.flush() # Gera IDs mas mantém a transação
				te_class_id = get_te_class(te_class_name)
				if not te_class_id:
					print(f"TE class '{te_class_name}' not found in the database")
					session.rollback()
					quit()
				new_sequence_te_class = {
					"sequence_id": new_sequence_obj.id,
					"te_class_id": te_class_id
				}
				new_sequence_te_class_obj = SequenceTEClass(**new_sequence_te_class)
				session.add(new_sequence_te_class_obj)

			new_sequences.append(new_sequence_obj)
			if len(new_sequences) >= 400:
				session.commit()

				new_sequences = []

				step = 10 ** int(math.log10(total_sequences))
				if counter % step == 0:
					logger.debug(f"{counter}/{total_sequences} sequences processed and committed...")

		logger.info(f"✅  All {total_sequences} sequences added to the database successfully.")
		return len(fasta_data.sequences.keys())
	
	except Exception as e:
		session.rollback()
		print_log_error(logger, f"Failed while inserting sequence {counter} from '{filename}': {e}")
		exit(1)



try:
	thisFileName = os.path.basename(__file__)
	#log variables
	log_dir = args.log_dir  #log dir path
	log_file_name = "add_species"   #log file names
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

	Species = Base.classes.species
	Sequence = Base.classes.sequences
	LiteratureItem = Base.classes.literature
	TEClass = Base.classes.te_classes
	SequenceTEClass = Base.classes.sequence_te_class

	# Create a Session
	Session = sessionmaker(bind=engine)
	

	logger.debug(f"Reading species file: {args.species_file}")
	# Loop over species file and add to DB
	species_file = open(args.species_file, 'r')

	for line in species_file:
		if line.startswith("#"):
			continue
		line = line.rstrip()
		name, code, genome_source, genome_version, doi = line.split("\t")

		logger.info(f"Inserting species '{name}' data  ===============================================")
		
		# skip if species exists
		session = Session()

		try:
			species = session.query(Species).filter_by(code=code).first()

			if species:
				logger.info(f"'{name}' data  already in database. Skipping to next species")
				continue  # antes de fechar a sessão, então use try/finally para fechar

			# add literature
			if doi != '-':
				literature_id = add_literature(doi, session)
				time.sleep(3)
			else:
				literature_id = None

			# add species (se essa função usar sessão, deve receber 'session', não 'engine')
			species_id = add_species(code, name, session, source=genome_source, literature_id=literature_id, genome_version=genome_version)

			# add sequences
			num_seq_added_cds = add_from_fasta(code, species_id, sequence_type='protein_coding')
			num_seq_added_rna = add_from_fasta(code, species_id, sequence_type='RNA')
			num_seq_added_te = add_from_fasta(code, species_id, sequence_type='TE')

			logger.info(f"✅  Added {num_seq_added_cds} CDS and {num_seq_added_rna} RNA sequences for {name} ({code})\n")

			session.commit()
		except Exception as e:
			session.rollback()
			logger.error(f"Error processing species {name} ({code}): {e}")
			raise
		finally:
			session.close()


	session.close()

except Exception as e:
	print_log_error(logger, e)
	logger.info(f" ---- ❌ An error occurred while executing {thisFileName}. Please fix the issue and rerun the script. ❌ ---- ")
	exit(1)



logger.info(f" ---- ✅ SUCCESS: All operations from {thisFileName} finished without errors! ✅ ---- ")