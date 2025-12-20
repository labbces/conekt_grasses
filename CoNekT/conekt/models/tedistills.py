from conekt import db
from conekt.models.relationships import sequence_tedistill, tedistill_xref, tedistill_te_class
from conekt.models.relationships.sequence_tedistill import SequenceTEdistillAssociation
from conekt.models.relationships.sequence_sequence_ecc import SequenceSequenceECCAssociation
from conekt.models.sequences import Sequence
from conekt.models.interpro import Interpro
from conekt.models.go import GO

import re
import json
from collections import defaultdict, Counter

from sqlalchemy.orm import joinedload, load_only
from sqlalchemy.sql import or_, and_
from sqlalchemy.dialects.mysql import LONGTEXT


SQL_COLLATION = None


class TEdistillMethod(db.Model):
	__tablename__ = 'tedistill_methods'
	id = db.Column(db.Integer, primary_key=True)
	method = db.Column(db.Text)
	tedistill_count = db.Column(db.Integer)

	tedistills = db.relationship('TEdistill', backref=db.backref('method', lazy='joined'),
							   lazy='dynamic',
							   cascade="all, delete-orphan",
							   passive_deletes=True)

	tree_methods = db.relationship('TreeMethod', backref=db.backref('ted_method', lazy='joined'),
								   lazy='dynamic',
								   cascade="all, delete-orphan",
								   passive_deletes=True)

	def __init__(self, method):
		self.method = method

	def __str__(self):
		return "%d. %s" % (self.id, self.method)

	def get_clade_distribution(self):
		"""
		Will calculate the frequency of clade (per gene) for each species and return a dict of dict with counts

		counts[species_id][clade_id] = number of genes from the species associated with the Clade based on the current
		tedistill method.

		:return: dict-of-dict with species_id, clade_id and then the count
		"""
		counts = defaultdict(lambda: defaultdict(lambda: 0))

		for tedistill in self.tedistills:
			if tedistill.clade is not None:
				for s in tedistill.sequences:
					counts[s.species_id][tedistill.clade_id] += 1

		return counts

	def get_te_class_distribution(self):
		"""
		Will calculate the frequency of the te_class (per gene) for each species and return a dict of dict with counts

		counts[species_id][te_class_id] = number of genes from the species associated with the TE Class based on the
		current tedistill method.

		:return: dict-of-dict with species_id, te_class_id and then the count
		"""
		counts = defaultdict(lambda: defaultdict(lambda: 0))

		for tedistill in self.tedistills:
			if tedistill.te_class is not None:
				for s in tedistill.sequences:
					counts[s.species_id][tedistill.clade_id] += 1

		return counts

	@staticmethod
	def update_count():
		"""
		To avoid long count queries, the number of tedistills for a given method can be precalculated and stored in
		the database using this function.
		"""
		methods = TEdistillMethod.query.all()

		for m in methods:
			m.tedistill_count = m.tedistills.count()

		try:
			db.session.commit()
		except Exception as e:
			db.session.rollback()
			print(e)

	@staticmethod
	def add(description):
		new_method = TEdistillMethod(description)

		try:
			db.session.add(new_method)
			db.session.commit()
		except Exception as e:
			db.session.rollback()
			raise e

		return new_method


class TEdistill(db.Model):
	__tablename__ = 'tedistills'
	id = db.Column(db.Integer, primary_key=True)
	method_id = db.Column(db.Integer, db.ForeignKey('tedistill_methods.id', ondelete='CASCADE'), index=True)
	name = db.Column(db.String(50, collation=SQL_COLLATION), unique=True, index=True)
	representative_sequence = db.deferred(db.Column(LONGTEXT))
	clade_id = db.Column(db.Integer, db.ForeignKey('clades.id', ondelete='SET NULL'), index=True)

	# Original name is used to keep track of the original ID from OrthoFinder (required to link back to trees)
	original_name = db.Column(db.String(50, collation=SQL_COLLATION), index=True, default=None)

	sequences = db.relationship('Sequence', secondary=sequence_tedistill, lazy='dynamic')
	te_classes = db.relationship('TEClass', secondary=tedistill_te_class, lazy='dynamic')
	trees = db.relationship('Tree', backref='tedistill', lazy='dynamic')

	xrefs = db.relationship('XRef', secondary=tedistill_xref, lazy='dynamic')

	def __init__(self, name):
		self.name = name

	@property
	def species_codes(self):
		"""
		Finds all species the tedistill has genes from
		:return: a list of all species (codes)
		"""

		sequences = self.sequences.options(joinedload('species')).all()

		output = []

		for s in sequences:
			if s.species.code not in output:
				output.append(s.species.code)

		return output

	@property
	def species_counts(self):
		"""
		Generates a phylogenetic profile of a tedistill
		:return: a dict with counts per species (codes are keys)
		"""

		sequences = self.sequences.options(joinedload('species')).all()

		output = {}

		for s in sequences:
			if s.species.code not in output:
				output[s.species.code] = 1
			else:
				output[s.species.code] += 1

		return output

	@property
	def ecc_associations(self):
		sequence_ids = [s.id for s in self.sequences.all()]

		output = SequenceSequenceECCAssociation.query\
			.filter_by(tedistill_method_id=self.method_id)\
			.filter(or_(or_(*[SequenceSequenceECCAssociation.query_id == s for s in sequence_ids]),
						or_(*[SequenceSequenceECCAssociation.target_id == s for s in sequence_ids])))\
			.all()

		return output

	def ecc_associations_paginated(self, page=1, page_items=30):
		sequence_ids = [s.id for s in self.sequences.all()]

		output = SequenceSequenceECCAssociation.query\
			.filter_by(tedistill_method_id=self.method_id)\
			.filter(or_(or_(*[SequenceSequenceECCAssociation.query_id == s for s in sequence_ids]),
						or_(*[SequenceSequenceECCAssociation.target_id == s for s in sequence_ids])))\
			.paginate(page, page_items, False).items

		return output

	@staticmethod
	def sequence_stats(sequence_ids):
		"""
		Takes a list of sequence IDs and returns InterPro stats for those sequences

		:param sequence_ids: list of sequence ids
		:return: dict with for each InterPro domain linked with any of the input sequences stats
		"""
		data = SequenceTEdistillAssociation.query.filter(SequenceTEdistillAssociation.sequence_id.in_(sequence_ids)).all()

		return TEdistill.__sequence_stats_associations(data)

	@staticmethod
	def sequence_stats_subquery(sequences):
		"""
		Same as sequence_stats but takes a BaseQuery returning sequences as input (to avoid multiple times querying
		sequences by ID)

		:param sequences: BaseQuery returning sequences
		:return: dict with for each InterPro domain linked with any of the input sequences stats
		"""
		subquery = sequences.subquery()

		data = SequenceTEdistillAssociation.query.join(subquery, SequenceTEdistillAssociation.sequence_id == subquery.c.id).all()

		return TEdistill.__sequence_stats_associations(data)

	@staticmethod
	def __sequence_stats_associations(associations):
		output = {}
		for d in associations:
			if d.tedistill_id not in output.keys():
				output[d.tedistill_id] = {
					'tedistill': d.tedistill,
					'count': 1,
					'sequences': [d.sequence_id],
					'species': [d.sequence.species_id]
				}
			else:
				output[d.tedistill_id]['count'] += 1
				if d.sequence.species_id not in output[d.tedistill_id]['species']:
					output[d.tedistill_id]['species'].append(d.sequence.species_id)

		for k, v in output.items():
			v['species_count'] = len(v['species'])

		return output

	@staticmethod
	def __add_tedistills(tedistills, tedistill_members):
		"""
		Adds tedistills to the database and assigns genes to their designated tedistill

		:param tedistills: list of TEdistill objects
		:param tedistill_members: dict (keys = tedistill name) with lists of members
		"""
		for i, t in enumerate(tedistills):
			db.session.add(t)

			if i > 0 and i % 400 == 0:
				# Commit to DB every 400 records
				try:
					db.session.commit()
				except Exception as e:
					db.session.rollback()
					quit()

		try:
			# Commit to DB remainder
			db.session.commit()
		except Exception as e:
			db.session.rollback()
			quit()

		for i, t in enumerate(tedistills):
			for member in tedistill_members[t.name]:
				association = SequenceTEdistillAssociation()

				association.sequence_id = member.id
				association.tedistill_id = t.id

				db.session.add(association)

				if i > 0 and i % 400 == 0:
					# Commit to DB every 400 records
					try:
						db.session.commit()
					except Exception as e:
						db.session.rollback()
						quit()

		try:
			# Commit to DB remainder
			db.session.commit()
		except Exception as e:
			db.session.rollback()
			quit()

	@staticmethod
	def add_tedistills_from_mcl(filename, description, handle_isoforms=False, prefix='mcl'):
		"""
		Add tedistills directly from MCL output (one line with all genes from one tedistill)

		:param filename: The file to load
		:param description: Description of the method to store in the database
		:param handle_isoforms: should isoforms (indicated by .1 at the end) be handled
		:return the new methods internal ID
		"""
		# Create new method for these tedistills
		method = TEdistillMethod.add(description)

		gene_hash = {}
		all_sequences = Sequence.query.all()

		for sequence in all_sequences:
			gene_hash[sequence.name.lower()] = sequence

			if handle_isoforms:
				gene_id = re.sub('\.\d+$', '', sequence.name.lower())
				gene_hash[gene_id] = sequence

		tedistills = []
		tedistill_members = defaultdict(list)

		with open(filename, "r") as f_in:
			for i, line in enumerate(f_in, start=1):
				parts = line.strip().split()

				new_tedistill = TEdistill('%s_%02d_%08d' % (prefix, method.id, i))
				new_tedistill.original_name = None
				new_tedistill.method_id = method.id

				tedistills.append(new_tedistill)

				for p in parts:
					if p.lower() in gene_hash.keys():
						tedistill_members[new_tedistill.name].append(gene_hash[p.lower()])

		# add all tedistills

		TEdistill.__add_tedistills(tedistills, tedistill_members)

		return method.id

	@staticmethod
	def add_tedistills_from_orthofinder(filename, description, handle_isoforms=False):
		"""
		Add tedistills directly from OrthoFinder output (one line with all genes from one tedistill)

		:param filename: The file to load
		:param description: Description of the method to store in the database
		:param handle_isoforms: should isoforms (indicated by .1 at the end) be handled
		:return the new methods internal ID
		"""
		# Create new method for these tedistills
		method = TEdistillMethod.add(description)

		gene_hash = {}
		all_sequences = Sequence.query.filter_by(type='protein_coding').all()

		for sequence in all_sequences:
			gene_hash[sequence.name.lower()] = sequence

			if handle_isoforms:
				gene_id = re.sub('\.\d+$', '', sequence.name.lower())
				gene_hash[gene_id] = sequence

		tedistills = []
		tedistill_members = defaultdict(list)

		with open(filename, "r") as f_in:
			for line in f_in:
				orthofinder_id, *parts = line.strip().split()

				orthofinder_id = orthofinder_id.rstrip(':')

				new_tedistill = TEdistill(orthofinder_id.replace('OG', 'OG_%02d_' % method.id))
				new_tedistill.original_name = orthofinder_id
				new_tedistill.method_id = method.id

				tedistills.append(new_tedistill)

				for p in parts:
					if p.lower() in gene_hash.keys():
						tedistill_members[new_tedistill.name].append(gene_hash[p.lower()])

		# add all tedistills

		TEdistill.__add_tedistills(tedistills, tedistill_members)

		return method.id

	@staticmethod
	def add_tedistills_general(filename, description, handle_isoforms=False):
		"""
		Add tedistills directly from General file format output. This is the same as OrthoFinder but the identifier
		will be left alone

		:param filename: The file to load
		:param description: Description of the method to store in the database
		:param handle_isoforms: should isoforms (indicated by .1 at the end) be handled
		:return the new methods internal ID
		"""
		# Create new method for these tedistills
		method = TEdistillMethod.add(description)

		gene_hash = {}
		all_sequences = Sequence.query.all()

		for sequence in all_sequences:
			gene_hash[sequence.name.lower()] = sequence

			if handle_isoforms:
				gene_id = re.sub('\.\d+$', '', sequence.name.lower())
				gene_hash[gene_id] = sequence

		tedistills = []
		tedistill_members = defaultdict(list)

		with open(filename, "r") as f_in:
			for line in f_in:
				ted_id, *parts = line.strip().split()

				ted_id = ted_id.rstrip(':')

				new_tedistill = TEdistill(ted_id)
				new_tedistill.original_name = ted_id
				new_tedistill.method_id = method.id

				tedistills.append(new_tedistill)

				for p in parts:
					if p.lower() in gene_hash.keys():
						tedistill_members[new_tedistill.name].append(gene_hash[p.lower()])

		# add all tedistills

		TEdistill.__add_tedistills(tedistills, tedistill_members)

		return method.id