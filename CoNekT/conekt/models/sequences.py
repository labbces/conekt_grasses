from conekt import db, whooshee

from conekt.models.relationships import sequence_go, sequence_interpro, sequence_cazyme, sequence_family, sequence_cluster, sequence_tr
from conekt.models.relationships import sequence_xref, sequence_sequence_ecc
from utils.sequence import translate
from utils.parser.fasta import Fasta

from sqlalchemy.orm import undefer
from sqlalchemy.dialects.mysql import LONGTEXT
import operator
import sys

SQL_COLLATION = None


@whooshee.register_model('description')
class Sequence(db.Model):
    __tablename__ = 'sequences'
    id = db.Column(db.Integer, primary_key=True)
    species_id = db.Column(db.Integer, db.ForeignKey('species.id', ondelete='CASCADE'), index=True)
    name = db.Column(db.String(80, collation=SQL_COLLATION), index=True)
    description = db.Column(db.Text)
    coding_sequence = db.deferred(db.Column(LONGTEXT))
    type = db.Column(db.Enum('protein_coding', 'TE', 'RNA', name='sequence_type'), default='protein_coding')
    is_mitochondrial = db.Column(db.SmallInteger, default=False)
    is_chloroplast = db.Column(db.SmallInteger, default=False)

    expression_profiles = db.relationship('ExpressionProfile', backref=db.backref('sequence', lazy='joined'),
                                          lazy='dynamic',
                                          cascade="all, delete-orphan",
                                          passive_deletes=True)
    network_nodes = db.relationship('ExpressionNetwork',
                                    backref=db.backref('sequence', lazy='joined'),
                                    lazy='dynamic',
                                    cascade="all, delete-orphan",
                                    passive_deletes=True)

    # Other properties
    #
    # coexpression_cluster_associations declared in 'SequenceCoexpressionClusterAssociation'
    # interpro_associations declared in 'SequenceInterproAssociation'
    # go_associations declared in 'SequenceGOAssociation'
    # cazyme_associations declared in 'SequenceCAZYmeAssociation'
    # family_associations declared in 'SequenceFamilyAssociation'

    go_labels = db.relationship('GO', secondary=sequence_go, lazy='dynamic')
    interpro_domains = db.relationship('Interpro', secondary=sequence_interpro, lazy='dynamic')
    cazymes = db.relationship('CAZYme', secondary=sequence_cazyme, lazy='dynamic')
    trs = db.relationship('TranscriptionRegulator',
                          secondary=sequence_tr,
                          backref=db.backref('sequences_trs', lazy='dynamic'),
                          lazy='dynamic')
    families = db.relationship('GeneFamily', secondary=sequence_family, lazy='dynamic')

    coexpression_clusters = db.relationship('CoexpressionCluster', secondary=sequence_cluster,
                                            backref=db.backref('sequences', lazy='dynamic'),
                                            lazy='dynamic')

    ecc_query_associations = db.relationship('SequenceSequenceECCAssociation',
                                             primaryjoin="SequenceSequenceECCAssociation.query_id == Sequence.id",
                                             backref=db.backref('query_sequence', lazy='joined'),
                                             lazy='dynamic')

    ecc_target_associations = db.relationship('SequenceSequenceECCAssociation',
                                              primaryjoin="SequenceSequenceECCAssociation.target_id == Sequence.id",
                                              backref=db.backref('target_sequence', lazy='joined'),
                                              lazy='dynamic')

    clade_associations_one = db.relationship('SequenceSequenceCladeAssociation',
                                             primaryjoin="SequenceSequenceCladeAssociation.sequence_one_id == Sequence.id",
                                             backref=db.backref('sequence_one', lazy='joined'),
                                             lazy='dynamic')

    clade_associations_two = db.relationship('SequenceSequenceCladeAssociation',
                                             primaryjoin="SequenceSequenceCladeAssociation.sequence_two_id == Sequence.id",
                                             backref=db.backref('sequence_two', lazy='joined'),
                                             lazy='dynamic')

    xrefs = db.relationship('XRef', secondary=sequence_xref, lazy='joined')

    def __init__(self, species_id, name, coding_sequence, type='protein_coding', is_chloroplast=False,
                 is_mitochondrial=False, description=None):
        self.species_id = species_id
        self.name = name
        self.description = description
        self.coding_sequence = coding_sequence
        self.type = type
        self.is_chloroplast = is_chloroplast
        self.is_mitochondrial = is_mitochondrial

    @property
    def protein_sequence(self):
        """
        Function to translate the coding sequence to the amino acid sequence. Will start at the first start codon and
        break after adding a stop codon (indicated by '*')

        :return: The amino acid sequence based on the coding sequence
        """
        return translate(self.coding_sequence)

    @property
    def aliases(self):
        """
        Returns a readable string with the aliases or tokens stored for this sequence in the table xrefs

        :return: human readable string with aliases or None
        """
        t = [x.name for x in self.xrefs if x.platform == 'token']

        return ", ".join(t) if len(t) > 0 else None

    @property
    def shortest_alias(self):
        """
        Returns the shortest alias

        :return: string with shortest alias or None (in case no aliases exist)
        """
        t = [x.name for x in self.xrefs if x.platform == 'token']

        return min(t, key=len) if len(t) > 0 else None

    @property
    def display_name(self):
        """
        Returns a name to display (from xrefs with display) if available otherwise return name

        :return: display name
        """
        t = [x.name for x in self.xrefs if x.platform == 'display']

        return t[0] if len(t) > 0 else self.name

    @property
    def best_name(self):
        """
        Checks if there is a display name, if not checks the shortest alias, otherwise returns name. To be used in e.g.
        graphs

        :return: string with best name to show in graphs, ...
        """
        if self.display_name is not self.name:
            return self.display_name
        elif self.shortest_alias is not None:
            return self.shortest_alias
        else:
            return self.name

    @property
    def readable_type(self):
        """
        Converts the type table to a readable string

        :return: string with readable version of the sequence type
        """
        conversion = {'protein_coding': 'protein coding',
                      'TE': 'transposable element',
                      'RNA': 'RNA'}

        if self.type in conversion.keys():
            return conversion[self.type]
        else:
            return 'other'
