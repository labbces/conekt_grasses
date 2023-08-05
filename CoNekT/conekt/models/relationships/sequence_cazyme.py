from conekt import db

import json


class SequenceCAZYmeAssociation(db.Model):
    __tablename__ = 'sequence_cazyme'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    sequence_id = db.Column(db.Integer, db.ForeignKey('sequences.id', ondelete='CASCADE'))
    cazyme_id = db.Column(db.Integer, db.ForeignKey('cazyme.id', ondelete='CASCADE'))
    hmm_length = db.Column(db.Integer, default=None)
    query_length = db.Column(db.Integer, default=None)
    e_value = db.Column(db.Text)
    query_start = db.Column(db.Integer, default=None)
    query_end = db.Column(db.Integer, default=None)


    sequence = db.relationship('Sequence', backref=db.backref('cazyme_associations',
                                                              lazy='dynamic',
                                                              passive_deletes=True), lazy='joined')

    cazyme = db.relationship('CAZYme', backref=db.backref('sequence_associations',
                                                  lazy='dynamic',
                                                  passive_deletes=True), lazy='joined')

    def __init__(self, sequence_id, cazyme_id, hmm_length, query_length, e_value, query_start, query_end):
        self.sequence_id = sequence_id
        self.cazyme_id = cazyme_id
        self.hmm_length = hmm_length
        self.query_length = query_length
        self.e_value = e_value
        self.query_start = query_start
        self.query_end = query_end