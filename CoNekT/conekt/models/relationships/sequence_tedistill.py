from conekt import db


class SequenceTEdistillAssociation(db.Model):
    __tablename__ = 'sequence_tedistill'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    sequence_id = db.Column(db.Integer, db.ForeignKey('sequences.id', ondelete='CASCADE'))
    tedistill_id = db.Column(db.Integer, db.ForeignKey('tedistills.id', ondelete='CASCADE'))

    sequence = db.relationship('Sequence', backref=db.backref('tedistill_associations',
                                                              lazy='dynamic',
                                                              passive_deletes=True), lazy='joined')
    tedistill = db.relationship('TEdistill', backref=db.backref('sequence_associations',
                                                              lazy='dynamic',
                                                              passive_deletes=True), lazy='joined')


