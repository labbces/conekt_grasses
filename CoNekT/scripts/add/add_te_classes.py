#!/usr/bin/env python3

import getpass
import argparse
import pandas as pd
from collections import defaultdict

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select

from log_functions import *

parser = argparse.ArgumentParser(description='Add tedistill sequences to the database')
parser.add_argument('--te_classes', type=str, metavar='TE Classes tsv',
					dest='te_classes_file',
					help='The TE Classes tsv file',
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


def add_te_class_method(description, engine):
	logger.info(f"Adding TEClassMethod: {description}")

	with engine.connect() as conn:
		logger.debug(f"🔍 Checking if TEClassMethod '{description}' already exists...")
		stmt = select([TEClassMethod]).where(TEClassMethod.__table__.c.method == description)
		method = conn.execute(stmt).first()
		
		if method:
			print(f"⚠️ TEClassMethod '{description}' already exists in the database")
			exit(1)

	try:
		logger.debug(f"📝 Inserting new TEClassMethod: {description}")
		session.add(TEClassMethod(method=description))
		session.commit()
		logger.debug("✅ TEClassMethod committed successfully.")
	except Exception as e:
		session.rollback()
		print_log_error(logger, e)
		raise e

def add_te_class(te_class_name, method):

	with engine.connect() as conn:
		stmt = select(TEClass.__table__.c).where(TEClass.name == te_class_name)
		te_class = conn.execute(stmt).first()

	# TE class is not in the DB yet, add it
	if not te_class:
		# TE class is expected in this format: level1/level2-level3, or level1/level2 or level1
		level1, level2, level3 = None, None, None
		if len(te_class_name.split('/')) > 1:
			aux = te_class_name.split('/')[1]
			if len(aux.split('-')) > 1:
				level3 = aux.split('-')[1]
			level2 = aux.split('-')[0]
		level1 = te_class_name.split('/')[0]

		new_te_class = {"name": te_class_name,
						"level1": level1,
						"level2": level2,
				 		"level3": level3,
						"method_id": method.id
					}

		new_te_class_obj = TEClass(**new_te_class)
		session.add(new_te_class_obj)
	else:
		print(f"TEClass '{te_class_name}' already exists in the database")

def add_te_classes_from_tsv(te_classes_file, description, engine):
		"""
		Add gene tedistills directly from OrthoFinder output (one line with all genes from one tedistill)

		:param filename: The file to load
		:param description: Description of the method to store in the database
		:return the new methods internal ID
		"""
		logger.info(f"📂 Processing tsv file: {te_classes_file}")
		add_te_class_method(description, engine)

		with engine.connect() as conn:
			stmt = select(TEClassMethod.__table__.c).where(TEClassMethod.method == description)
			method = conn.execute(stmt).first()
			logger.debug(f"✅ Using TEClassMethod ID {method.id} for classes.")

		tsv_data = pd.read_csv(te_classes_file, sep="\t")

		# Loop over sequences, sorted by name (key here) and add to db
		for index, row in tsv_data.iterrows():
			te_class = row['te_class']
			add_te_class(te_class, method)

			if index % 40 == 0:
				# commit to the db frequently to allow WHOOSHEE's indexing function to work without timing out
				try:
					logger.debug(f"📦 Committing batch of {index} classes...")
					session.commit()
				except Exception as e:
					session.rollback()
					print(e)
					quit()

		try:
			# Commit to DB remainder
			session.commit()
		except Exception as e:
			session.rollback()
			print(e)
			quit()


try:
	thisFileName = os.path.basename(__file__)
	log_dir = args.log_dir
	log_file_name = "te_classes"
	db_verbose = str2bool(args.db_verbose)
	py_verbose = str2bool(args.py_verbose)
	logger = setup_logger(log_dir=log_dir, base_filename=log_file_name, DBverbose=db_verbose, PYverbose=py_verbose)

	create_engine_string = f"mysql+pymysql://{args.db_admin}:{db_password}@localhost/{args.db_name}"
	engine = create_engine(create_engine_string, echo=False)

	Base = automap_base()
	Base.prepare(engine, reflect=True)

	TEClassMethod = Base.classes.te_class_methods
	TEClass = Base.classes.te_classes

	Session = sessionmaker(bind=engine)
	session = Session()

	add_te_classes_from_tsv(args.te_classes_file, args.description, engine)

	session.close()

except Exception as e:
	print_log_error(logger, e)
	logger.info(f" ---- ❌ An error occurred while executing {thisFileName}. Please fix the issue and rerun the script. ❌ ---- ")
	exit(1)

logger.info(f" ---- ✅ SUCCESS: All operations from {thisFileName} finished without errors! ✅ ---- ")