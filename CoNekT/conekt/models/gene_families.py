from conekt import db
from conekt.models.relationships import sequence_family, family_xref, family_interpro
from conekt.models.relationships.sequence_family import SequenceFamilyAssociation
from conekt.models.relationships.sequence_sequence_ecc import SequenceSequenceECCAssociation
from conekt.models.interpro import Interpro
from conekt.models.go import GO

from sqlalchemy.orm import joinedload
from sqlalchemy.sql import or_

SQL_COLLATION = 'NOCASE' if db.engine.name == 'sqlite' else ''


class GeneFamilyMethod(db.Model):
    __tablename__ = 'gene_family_methods'
    id = db.Column(db.Integer, primary_key=True)
    method = db.Column(db.Text)
    family_count = db.Column(db.Integer)

    families = db.relationship('GeneFamily', backref=db.backref('method', lazy='joined'),
                               lazy='dynamic',
                               cascade="all, delete-orphan",
                               passive_deletes=True)

    tree_methods = db.relationship('TreeMethod', backref=db.backref('gf_method', lazy='joined'),
                                   lazy='dynamic',
                                   cascade="all, delete-orphan",
                                   passive_deletes=True)

    def __init__(self, method):
        self.method = method

    def __str__(self):
        return "%d. %s" % (self.id, self.method)


class GeneFamily(db.Model):
    __tablename__ = 'gene_families'
    id = db.Column(db.Integer, primary_key=True)
    method_id = db.Column(db.Integer, db.ForeignKey('gene_family_methods.id', ondelete='CASCADE'), index=True)
    name = db.Column(db.String(50, collation=SQL_COLLATION), unique=True, index=True)
    clade_id = db.Column(db.Integer, db.ForeignKey('clades.id', ondelete='SET NULL'), index=True)

    # Original name is used to keep track of the original ID from OrthoFinder (required to link back to trees)
    original_name = db.Column(db.String(50, collation=SQL_COLLATION), index=True, default=None)

    sequences = db.relationship('Sequence', secondary=sequence_family, lazy='dynamic')
    trees = db.relationship('Tree', backref='family', lazy='dynamic')

    interpro_domains = db.relationship('Interpro', secondary=family_interpro, lazy='dynamic')
    xrefs = db.relationship('XRef', secondary=family_xref, lazy='dynamic')

    # Other properties
    # go_annotations from .relationships.family_go FamilyGOAssociation
    # interpro_annotations from .relationships.family_intpro FamilyInterproAssociation

    def __init__(self, name):
        self.name = name

    @property
    def species_codes(self):
        """
        Finds all species the family has genes from
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
        Generates a phylogenetic profile of a gene family
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
            .filter_by(gene_family_method_id=self.method_id)\
            .filter(or_(or_(*[SequenceSequenceECCAssociation.query_id == s for s in sequence_ids]),
                        or_(*[SequenceSequenceECCAssociation.target_id == s for s in sequence_ids])))\
            .all()

        return output

    @property
    def trs_associations(self):
        """Return unique TRs from sequences in this family, ordered by TR family name."""
        from conekt.models.tr import TranscriptionRegulator
        from conekt.models.sequences import Sequence
        from conekt.models.relationships.sequence_family import SequenceFamilyAssociation

        return (TranscriptionRegulator.query
                .join(TranscriptionRegulator.sequences) 
                .join(SequenceFamilyAssociation, Sequence.id == SequenceFamilyAssociation.sequence_id)
                .filter(SequenceFamilyAssociation.gene_family_id == self.id)
                .distinct()
                .all())

    def ecc_associations_paginated(self, page=1, page_items=30):
        sequence_ids = [s.id for s in self.sequences.all()]

        output = SequenceSequenceECCAssociation.query\
            .filter_by(gene_family_method_id=self.method_id)\
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
        data = SequenceFamilyAssociation.query.filter(SequenceFamilyAssociation.sequence_id.in_(sequence_ids)).all()

        return GeneFamily.__sequence_stats_associations(data)

    @staticmethod
    def sequence_stats_subquery(sequences):
        """
        Same as sequence_stats but takes a BaseQuery returning sequences as input (to avoid multiple times querying
        sequences by ID)

        :param sequences: BaseQuery returning sequences
        :return: dict with for each InterPro domain linked with any of the input sequences stats
        """
        subquery = sequences.subquery()

        data = SequenceFamilyAssociation.query.join(subquery, SequenceFamilyAssociation.sequence_id == subquery.c.id).all()

        return GeneFamily.__sequence_stats_associations(data)

    @staticmethod
    def __sequence_stats_associations(associations):
        output = {}
        for d in associations:
            if d.gene_family_id not in output.keys():
                output[d.gene_family_id] = {
                    'family': d.family,
                    'count': 1,
                    'sequences': [d.sequence_id],
                    'species': [d.sequence.species_id]
                }
            else:
                output[d.gene_family_id]['count'] += 1
                if d.sequence.species_id not in output[d.gene_family_id]['species']:
                    output[d.gene_family_id]['species'].append(d.sequence.species_id)

        for k, v in output.items():
            v['species_count'] = len(v['species'])

        return output

    @property
    def interpro_stats(self):
        return Interpro.sequence_stats_subquery(self.sequences)

    @property
    def go_stats(self):
        return GO.sequence_stats_subquery(self.sequences)

    @property
    def family_stats(self):
        return GeneFamily.sequence_stats_subquery(self.sequences)
