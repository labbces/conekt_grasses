from conekt import db


class SequenceTEClassAssociation(db.Model):
    __tablename__ = 'sequence_te_class'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    sequence_id = db.Column(db.Integer, db.ForeignKey('sequences.id', ondelete='CASCADE'))
    te_class_id = db.Column(db.Integer, db.ForeignKey('te_classes.id', ondelete='CASCADE'))

    sequence = db.relationship('Sequence', backref=db.backref('te_class_associations',
                                                              lazy='dynamic',
                                                              passive_deletes=True), lazy='joined')
    te_class = db.relationship('TEClass', backref=db.backref('sequence_associations',
                                                              lazy='dynamic',
                                                              passive_deletes=True), lazy='joined')


