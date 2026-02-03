from conekt import db
from conekt.models.relationships import sequence_te_class, te_class_xref, tedistill_te_class, te_class_so
from conekt.models.relationships.sequence_te_class import SequenceTEClassAssociation
from conekt.models.relationships.sequence_sequence_ecc import SequenceSequenceECCAssociation
from conekt.models.sequences import Sequence
from conekt.models.interpro import Interpro
from conekt.models.go import GO

import re
import json
from collections import defaultdict, Counter

from sqlalchemy.orm import joinedload, load_only
from sqlalchemy.sql import or_, and_

SQL_COLLATION = None


class TEClassMethod(db.Model):
    __tablename__ = 'te_class_methods'
    id = db.Column(db.Integer, primary_key=True)
    method = db.Column(db.Text)
    te_class_count = db.Column(db.Integer)

    te_classes = db.relationship('TEClass', backref=db.backref('method', lazy='joined'),
                               lazy='dynamic',
                               cascade="all, delete-orphan",
                               passive_deletes=True)

    tree_methods = db.relationship('TreeMethod', backref=db.backref('tec_method', lazy='joined'),
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
        te_class method.

        :return: dict-of-dict with species_id, clade_id and then the count
        """
        counts = defaultdict(lambda: defaultdict(lambda: 0))

        for te_class in self.te_classes:
            if te_class.clade is not None:
                for s in te_class.sequences:
                    counts[s.species_id][te_class.clade_id] += 1

        return counts

    @staticmethod
    def update_count():
        """
        To avoid long count queries, the number of te_classes for a given method can be precalculated and stored in
        the database using this function.
        """
        methods = TEClassMethod.query.all()

        for m in methods:
            m.te_class_count = m.te_classes.count()

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)

    @staticmethod
    def add(description):
        new_method = TEClassMethod(description)

        try:
            db.session.add(new_method)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

        return new_method


class TEClass(db.Model):
    __tablename__ = 'te_classes'
    id = db.Column(db.Integer, primary_key=True)
    method_id = db.Column(db.Integer, db.ForeignKey('te_class_methods.id', ondelete='CASCADE'), index=True)
    name = db.Column(db.String(50, collation=SQL_COLLATION), unique=True, index=True)
    level1 = db.Column(db.String(50, collation=SQL_COLLATION))
    level2 = db.Column(db.String(50, collation=SQL_COLLATION))
    level3 = db.Column(db.String(50, collation=SQL_COLLATION))
    clade_id = db.Column(db.Integer, db.ForeignKey('clades.id', ondelete='SET NULL'), index=True)

    sequences = db.relationship('Sequence', secondary=sequence_te_class, lazy='dynamic')
    tedistills = db.relationship('TEdistill', secondary=tedistill_te_class, lazy='dynamic')
    trees = db.relationship('Tree', backref='te_class', lazy='dynamic')
    sequence_ontology_terms = db.relationship('SequenceOntology', secondary=te_class_so, lazy='dynamic')

    xrefs = db.relationship('XRef', secondary=te_class_xref, lazy='dynamic')

    def __init__(self, name):
        self.name = name

    @property
    def species_codes(self):
        """
        Finds all species the te_class has genes from
        :return: a list of all species (codes)
        """

        sequences = self.sequences.options(joinedload('species')).all()

        output = []

        for s in sequences:
            if s.species.code not in output:
                output.append(s.species.code)

        return output

    @property
    def sequence_ontology(self):
        """
        Returns the first sequence ontology term associated with this TE class
        :return: SequenceOntology object or None
        """
        return self.sequence_ontology_terms.first()

    @property
    def species_counts(self):
        """
        Generates a phylogenetic profile of a  te_class
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
            .filter_by(te_class_method_id=self.method_id)\
            .filter(or_(or_(*[SequenceSequenceECCAssociation.query_id == s for s in sequence_ids]),
                        or_(*[SequenceSequenceECCAssociation.target_id == s for s in sequence_ids])))\
            .all()

        return output

    def ecc_associations_paginated(self, page=1, page_items=30):
        sequence_ids = [s.id for s in self.sequences.all()]

        output = SequenceSequenceECCAssociation.query\
            .filter_by(te_class_method_id=self.method_id)\
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
        data = SequenceTEClassAssociation.query.filter(SequenceTEClassAssociation.sequence_id.in_(sequence_ids)).all()

        return TEClass.__sequence_stats_associations(data)

    @staticmethod
    def sequence_stats_subquery(sequences):
        """
        Same as sequence_stats but takes a BaseQuery returning sequences as input (to avoid multiple times querying
        sequences by ID)

        :param sequences: BaseQuery returning sequences
        :return: dict with for each InterPro domain linked with any of the input sequences stats
        """
        subquery = sequences.subquery()

        data = SequenceTEClassAssociation.query.join(subquery, SequenceTEClassAssociation.sequence_id == subquery.c.id).all()

        return TEClass.__sequence_stats_associations(data)

    @staticmethod
    def __sequence_stats_associations(associations):
        output = {}
        for d in associations:
            if d.te_class_id not in output.keys():
                output[d.te_class_id] = {
                    'te_class': d.te_class,
                    'count': 1,
                    'sequences': [d.sequence_id],
                    'species': [d.sequence.species_id]
                }
            else:
                output[d.te_class_id]['count'] += 1
                if d.sequence.species_id not in output[d.te_class_id]['species']:
                    output[d.te_class_id]['species'].append(d.sequence.species_id)

        for k, v in output.items():
            v['species_count'] = len(v['species'])

        return output

    @staticmethod
    def __add_te_classes(te_classes, te_class_members):
        """
        Adds te_classes to the database and assigns genes to their designated te_class

        :param te_classes: list of TEClass objects
        :param te_class_members: dict (keys = te_class name) with lists of members
        """
        for i, f in enumerate(te_classes):
            db.session.add(f)

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

        for i, f in enumerate(te_classes):
            for member in te_class_members[f.name]:
                association = SequenceTEClassAssociation()

                association.sequence_id = member.id
                association.te_class_id = f.id

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