#!/usr/bin/env python3

import getpass
import argparse
import operator

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select
from collections import defaultdict

from log_functions import *

from utils.fasta import Fasta

parser = argparse.ArgumentParser(description='Add tedistill sequences to the database')
parser.add_argument('--sequences', type=str, metavar='TEdisitll fasta',
					dest='sequences_file',
					help='The fasta file from TEdistill',
					required=True)
parser.add_argument('--orthogroups', type=str, metavar='Orthogroups_TEdistill.txt',
					dest='orthogroups_file',
					help='The Orthogroups_TEdistill.txt file from TEdistill',
					required=True)
parser.add_argument('--description', type=str, metavar='Description',
					dest='description',
					help='Description of the method as it should appear in CoNekT',
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

db_password = args.db_password if args.db_password else getpass.getpass("Enter the database password: ")


def get_te_class(te_class_name):

	with engine.connect() as conn:
		stmt = select(TEClass.__table__.c).where(TEClass.name == te_class_name)
		te_class = conn.execute(stmt).first()

	if te_class:
		return te_class.id
	else:
		return None

def add_tedistill_method(description, engine):
		with engine.connect() as conn:
			logger.debug(f"🔍 Checking if TEdistillMethod '{description}' already exists...")
			stmt = select([TEdistillMethod]).where(TEdistillMethod.__table__.c.method == description)
			method = conn.execute(stmt).first()
			if method:
				print(f"⚠️ TEdistill method '{description}' already exists in the database")
				exit(1)

		try:
			logger.debug(f"📝 Inserting new TEdistillMethod: {description}")
			session.add(TEdistillMethod(method=description))
			session.commit()
			logger.debug("✅ TEdistillMethod committed successfully.")
		except Exception as e:
			session.rollback()
			raise e


def add_tedistills(tedistills, tedistill_members):
		"""
		Adds TEdistills sequences to the database and assigns sequences to their designated TEdistill consense sequence

		:param tedistills: list of (TEdistill objects, TEClass id associated)
		:param tedistill_members: dict (keys = tedistill sequence name) with lists of members
		"""
		logger.debug(f"🧩 Adding {len(tedistills)} TEdistills...")

		for i, obj in enumerate(tedistills):
			t, c = obj

			session.add(t)

			session.flush() # Generate IDs keeping the transaction
			new_tedistill_te_class = TEdistillTEClassAssociation(tedistill_id=t.id)
			new_tedistill_te_class.te_class_id = c

			session.add(new_tedistill_te_class)
				
			if i > 0 and i % 400 == 0:
				logger.debug(f"📦 Committing batch of {i} TEdistills...")
				try:
					session.commit()
				except Exception as e:
					session.rollback()
					print_log_error(logger, e)
					quit()

		try:
			session.commit()
			logger.debug("✅ All TEdistills committed successfully.")
		except Exception as e:
			session.rollback()
			print_log_error(logger, e)
			quit()

		for i, obj in enumerate(tedistills):
			t, c = obj
			logger.debug(f"🔗 Linking sequences to TEdistills {t.name} (ID pending DB)...")

			with engine.connect() as conn:
				stmt = select([Sequence]).where(Sequence.__table__.c.id.in_(list(tedistill_members[t.name])))
				tedistill_sequences = conn.execute(stmt).fetchall()
				logger.debug(f"   ↳ Found {len(tedistill_sequences)} sequences for TEdistills {t.name}")
				exit

			for member in tedistill_sequences:
				association = SequenceTEdistillAssociation()
				
				association.sequence_id = member.id
				association.tedistill_id = t.id

				session.add(association)

				if i > 0 and i % 400 == 0:
					logger.debug(f"📦 Committing batch of {i} associations...")
					try:
						session.commit()
					except Exception as e:
						session.rollback()
						print_log_error(logger, e)
						quit()

			del tedistill_sequences

		try:
			session.commit()
			logger.debug("✅ All sequence-family associations committed successfully.")
		except Exception as e:
			session.rollback()
			quit()


def add_tedistills_from_orthofinder(orthogroups_file, sequences_file, description, engine):
		"""
		Add gene tedistills directly from OrthoFinder output (one line with all genes from one tedistill)

		:param filename: The file to load
		:param description: Description of the method to store in the database
		:return the new methods internal ID
		"""
		try:
			logger.info(f"📂 Processing OrthoFinder file: {orthogroups_file}")
			add_tedistill_method(description, engine)

			with engine.connect() as conn:
				stmt = select(TEdistillMethod.__table__.c).where(TEdistillMethod.method == description)
				method = conn.execute(stmt).first()
				logger.debug(f"✅ Using TEdistillMethod ID {method.id} for families.")

			gene_hash = {}
			logger.debug("🔍 Loading TE sequences from DB...")
			with engine.connect() as conn:
				stmt = select([Sequence.__table__.c.name, Sequence.__table__.c.id]).where(Sequence.__table__.c.type == 'TE')
				all_sequences = conn.execute(stmt).fetchall()
				logger.debug(f"✅ Loaded {len(all_sequences)} TE sequences.")

			for sequence in all_sequences:
				gene_hash[sequence.name.lower()] = sequence
			del all_sequences

			sequences_data = {}

			fasta_data = Fasta()
			fasta_data.readfile(sequences_file)

			# Loop over sequences, sorted by name (key here) and add to db
			for line, sequence in sorted(fasta_data.sequences.items(), key=operator.itemgetter(0)):
				name, te_class_name = line.split('#')
				name = name.strip('>')
				te_class_id = get_te_class(te_class_name)
				if not te_class_id:
					print(f"❌ TE class '{te_class_name}' not found in the database")
					session.rollback()
					quit()

				sequences_data[name] = {"te_class": te_class_id, "sequence": sequence}

			tedistills = set()
			tedistill_members = defaultdict(set)

			logger.debug(f"📖 Reading orthogroups from {orthogroups_file}...")
			with open(orthogroups_file, "r") as f_in:
				line_count = 0
				for line in f_in:
					line_count += 1
					if len(tedistills) >= 2000:
						logger.debug(f"📦 Reached 2000 TEdistills, committing batch...")
						add_tedistills(tedistills, tedistill_members)

						del tedistills
						del tedistill_members
						tedistills = set()
						tedistill_members = defaultdict(set)

					orthofinder_id, *parts = line.strip().split()
					orthofinder_id = orthofinder_id.rstrip(':')

					new_tedistill = TEdistill(name=orthofinder_id.replace('TE', 'TE_%02d' % method.id))
					new_tedistill.original_name = orthofinder_id
					new_tedistill.method_id = method.id
					new_tedistill.representative_sequence = sequences_data[new_tedistill.original_name]["sequence"]

					tedistills.add((new_tedistill, sequences_data[new_tedistill.original_name]["te_class"]))

					for p in parts:
						if p.lower() in gene_hash.keys():
							tedistill_members[new_tedistill.name].add(gene_hash[p.lower()][1])

					if line_count % 5000 == 0:
						logger.info(f"📊 Processed {line_count} lines from OrthoFinder file...")

			logger.debug(f"📦 Final batch commit with {len(tedistills)} families...")
			add_tedistills(tedistills, tedistill_members)
			logger.info(f"✅ Finished processing {line_count} lines from OrthoFinder file.")

		except Exception as e:
			print_log_error(logger, f'Error while adding tedistills from orthofinder: {e}')

try:
	thisFileName = os.path.basename(__file__)
	log_dir = args.log_dir
	log_file_name = "tedistills"
	db_verbose = str2bool(args.db_verbose)
	py_verbose = str2bool(args.py_verbose)
	logger = setup_logger(log_dir=log_dir, base_filename=log_file_name, DBverbose=db_verbose, PYverbose=py_verbose)

	create_engine_string = "mysql+pymysql://"+args.db_admin+":"+args.db_password+"@localhost/"+args.db_name
	engine = create_engine(create_engine_string, echo=False)

	Base = automap_base()
	Base.prepare(engine, reflect=True)

	TEdistillMethod = Base.classes.tedistill_methods
	TEdistill = Base.classes.tedistills
	Sequence = Base.classes.sequences
	TEClass = Base.classes.te_classes
	SequenceTEdistillAssociation = Base.classes.sequence_tedistill
	TEdistillTEClassAssociation = Base.classes.tedistill_te_class

	Session = sessionmaker(bind=engine)
	session = Session()

	add_tedistills_from_orthofinder(args.orthogroups_file, args.sequences_file, args.description, engine)

	session.close()
except Exception as e:
	print_log_error(logger, e)
	logger.info(f" ---- ❌ An error occurred while executing {thisFileName}. Please fix the issue and rerun the script. ❌ ---- ")
	exit(1)

logger.info(f" ---- ✅ SUCCESS: All operations from {thisFileName} finished without errors! ✅ ---- ")
